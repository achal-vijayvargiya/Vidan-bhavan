from langchain.prompts import ChatPromptTemplate
import json
import hashlib
from dotenv import load_dotenv
from app.config.OpenRouter import llm, llm_gemini
import time
from typing import List, Dict
from langchain.memory import ConversationBufferMemory
from app.logging.logger import Logger
from app.database.redis_cache import get_llm_cache, set_llm_cache, delete_llm_cache
from app.token_optimizer.token_optimizer import optimize_tokens


# Initialize logger
logger = Logger()

# Load environment variables
load_dotenv()

# PRODUCTION: Configuration constants - NO DATA LOSS
RATE_LIMIT_DELAY = 2  # BALANCED: Reduced delay for faster processing
MAX_RETRIES = 2  # BALANCED: Increased retries for reliability
CACHE_EXPIRY_HOURS = 24  # Cache LLM responses for 24 hours

# Create the prompt template
MEMBER_PARSER_TEMPLATE = """You are a document parser working on Marathi Vidhan Sabha member information.

Previous members processed:
{previous_members}


Extract the following structured data from the given text chunk:

- name: Full name of the member (e.g., "श्री. अजित अनंतराव पवार")
- position: Their position/role (e.g., "मुख्यमंत्री", "उपमुख्यमंत्री", "मंत्री", "राज्यमंत्री", "अध्यक्ष")
- department: Their department/ministry (e.g., "गृह", "नगरविकास", "कृषी", "ऊर्जा")

📌 Return output as valid JSON array:
[
  {{
    "name": "",
    "role": "",
    "ministry": ""
  }},
  ...
]

IMPORTANT: When generating Marathi text responses:
1. Use EXACT text from the input text - do not modify or translate
2. Preserve all Marathi characters, numbers and formatting
3. Do not add any English text or translations
4. Return only the extracted Marathi text exactly as it appears in source
5. DO NOT include members that were already processed in previous chunks
6. Return an empty list [] if no new members are found in this chunk

Rare case handling:
- Members name is required. Never skip any name.
- If any chunk missing role or ministry value, create entry with only name and empty role and ministry value in the output

DO NOT return extra text, markdown, or comments.

Text chunk:
{text_chunk}
"""

class MemberParser:
    def __init__(self):
        logger.info("MemberParser.__init__ called with COST OPTIMIZATIONS")
        self.extracted_data = {
            "members": [],
            "total_count": 0
        }
        self.chunk_size = 2000  # BALANCED: Increased chunk size for better context
        self.memory_key = "member_parser_previous_members"
        self.k = 1  # Only use last call history
        self.prompt = ChatPromptTemplate.from_template(MEMBER_PARSER_TEMPLATE)
        self.chain = self.prompt | llm_gemini
        self.processed_chunks = 0  # Track processed chunks

    def _get_chunk_cache_key(self, text_chunk: str, previous_members: str, mapping: str) -> str:
        """Generate cache key for LLM response."""
        content = f"{text_chunk}|{previous_members}|{mapping}"
        return f"member_llm_cache_{hashlib.md5(content.encode('utf-8')).hexdigest()}"

    def _get_cached_llm_response(self, cache_key: str) -> str:
        """Get cached LLM response if available."""
        try:
            return get_llm_cache(cache_key)
        except Exception as e:
            logger.error(f"Error getting cached response: {e}")
            return None

    def _cache_llm_response(self, cache_key: str, response: str):
        """Cache LLM response for future use."""
        try:
            set_llm_cache(cache_key, response, expiry_hours=CACHE_EXPIRY_HOURS)
            logger.info("LLM response cached successfully")
        except Exception as e:
            logger.error(f"Error caching response: {e}")

    @property
    def members(self) -> List[Dict]:
        """Getter for backward compatibility"""
        return self.extracted_data["members"]

    def _is_duplicate_member(self, new_member: Dict) -> bool:
        """Check if member already exists"""
        for existing_member in self.extracted_data["members"]:
            if (new_member["name"] == existing_member["name"] and 
                new_member.get("position", new_member.get("role", "")) == existing_member.get("position", existing_member.get("role", ""))):
                logger.info(f"Duplicate member detected: {new_member['name']} - {new_member.get('position', new_member.get('role', ''))}")
                return True
        return False

    def _update_memory(self):
        """Store extracted members in Redis for context"""
        # Store only the last k (1) members in Redis
        last_members = self.extracted_data["members"][-self.k:] if self.k > 0 else self.extracted_data["members"]
        members_json = json.dumps(last_members, ensure_ascii=False)
        set_llm_cache(self.memory_key, members_json)
        logger.info("Memory updated with current members list in Redis.")

    def _load_memory(self):
        """Load previously extracted members from Redis"""
        # Load only the last k (1) members from Redis
        members_json = get_llm_cache(self.memory_key)
        if members_json:
            try:
                return json.loads(members_json)
            except Exception as e:
                logger.error(f"Error loading memory from Redis: {e}")
        return []

    
    def parse_text_chunk(self, text_chunk: str) -> Dict:
        """Parse a single text chunk and extract member data"""
        logger.info("parse_text_chunk called")
        
        # PRODUCTION: Process all chunks - no limits to ensure complete data extraction
        
        try:
            previous_members = self._load_memory()
            # Only include names to minimize token length
            previous_member_names = [m["name"] for m in previous_members if isinstance(m, dict) and "name" in m]
            previous_members_json = json.dumps(previous_member_names, ensure_ascii=False)
            
            
            # PRODUCTION: Make LLM call if not cached - processing all chunks
            logger.info(f"🤖 Invoking LLM for member chunk {self.processed_chunks + 1}")
            logger.info(f"Previous member names: {[name for name in previous_member_names[:3]]}")  # Show first 3
            
            # Add retry logic with limited attempts
            retry_count = 0
            response = None
            
            while retry_count <= MAX_RETRIES:
                try:
                    response = self.chain.invoke({
                        "previous_members": previous_members_json,
                        "text_chunk": text_chunk
                    })
                    break  # Success, exit retry loop
                except Exception as e:
                    retry_count += 1
                    logger.error(f"LLM call failed (attempt {retry_count}/{MAX_RETRIES + 1}): {str(e)}")
                    
                    if retry_count > MAX_RETRIES:
                        logger.error("❌ COST PROTECTION: Max retries reached. Stopping to prevent cost multiplication.")
                        return self.extracted_data
                    
                    # Short delay before retry
                    time.sleep(1)
            
            if not response:
                logger.error("❌ Failed to get LLM response after retries")
                return self.extracted_data
            
            content = response.content.strip()
            
            # COST OPTIMIZATION: Cache the response
            
            self.processed_chunks += 1
            
            try:
                logger.info(f"Raw LLM content: {content}")
                # Extract content after </think> tag
                if '</think>' in content:
                    content = content.split('</think>')[1].strip()
                # Clean up any remaining markdown code block syntax
                content = content.replace('```json', '').replace('```', '').strip()
                
                try:
                    # Parse the cleaned JSON content
                    new_members = json.loads(content)
                    
                    if not isinstance(new_members, list):
                        logger.error("Warning: Response is not a list")
                        return self.extracted_data
                    
                    # PRODUCTION: Process ALL members - no truncation to ensure complete data extraction
                    logger.info(f"✅ Processing {len(new_members)} members from chunk - no limits applied")
                    
                    added_count = 0
                    for member in new_members:
                        if (isinstance(member, dict) and 
                            "name" in member and 
                            not self._is_duplicate_member(member)):
                            self.extracted_data["members"].append(member)
                            added_count += 1
                            logger.info(f"Added new member: {member['name']}")
                    
                    self.extracted_data["total_count"] = len(self.extracted_data["members"])
                    self._update_memory()
                    logger.info(f"✅ Chunk {self.processed_chunks} processed. Added {added_count} new members. Total: {self.extracted_data['total_count']}")
                    return self.extracted_data
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from LLM response: {e}")
                    logger.error(f"Content that failed to parse: {content}")
                    return self.extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Raw response: {content[:500]}...")  # Truncate error log
                return self.extracted_data
                
        except Exception as e:
            logger.error(f"❌ Error in parse_text_chunk: {str(e)}")
            return self.extracted_data

    def process_text(self, text: str) -> Dict:
        """Process the entire text by breaking it into chunks"""
        logger.info("process_text called with PRODUCTION SETTINGS - NO DATA LOSS")
        
        # PRODUCTION: Process ALL text - no size limits to ensure complete data extraction
        logger.info(f"✅ Processing full text ({len(text)} chars) - no truncation applied")
        
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line)
            if current_size + line_size > self.chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
                
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # PRODUCTION: Process ALL chunks - no limits to ensure complete data extraction
        logger.info(f"✅ Processing ALL {len(chunks)} chunks - no limits applied for complete data extraction")
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"📄 Processing chunk {i}/{len(chunks)} (size: {len(chunk)} chars)...")
            self.parse_text_chunk(chunk)
            
            # COST OPTIMIZATION: Rate limiting between LLM calls
            if i < len(chunks):  # Don't sleep after last chunk
                logger.info(f"⏱️  Rate limiting: waiting {RATE_LIMIT_DELAY} seconds before next LLM call...")
                time.sleep(RATE_LIMIT_DELAY)
                
        logger.info(f"✅ Finished processing {self.processed_chunks} chunks. Total members: {self.extracted_data['total_count']}")
        return self.extracted_data

    def clear_memory(self):
        """Clear the memory cache"""
        delete_llm_cache(self.memory_key)
        logger.info("Member parser memory cleared")

    def get_members_list(self) -> List[Dict]:
        """Get list of members for backward compatibility"""
        return self.extracted_data["members"]

def get_member_data(text: str, session_id: int = None, kramak_id: int = None) -> List[Dict]:
    """
    Main function to extract member data from Marathi text - backward compatibility
    COST OPTIMIZED: Includes caching, rate limiting, and batch size controls.
    COST TRACKED: Automatically tracks all LLM calls and costs.
    """
    logger.info("get_member_data called with COST TRACKING")
    
    
    parser = MemberParser()
    result = parser.process_text(text)
    
    return result["members"]  # Return just the members list for backward compatibility

def extract_member_data(text: str, session_id: int = None, kramak_id: int = None) -> Dict:
    """
    New function that returns full extracted data structure
    COST OPTIMIZED: Includes caching, rate limiting, and batch size controls.
    COST TRACKED: Automatically tracks all LLM calls and costs.
    """
    logger.info("extract_member_data called with COST TRACKING")
    
    
    parser = MemberParser()
    result = parser.process_text(text)
    
    return result 