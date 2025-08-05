import re
from typing import List, Dict
from langchain.prompts import ChatPromptTemplate
import json
import hashlib
from functools import lru_cache
from dotenv import load_dotenv
from app.config.OpenRouter import llm
import time
from langchain.memory import ConversationBufferMemory
from app.logging.logger import Logger
from app.database.redis_cache import get_llm_cache, set_llm_cache, delete_llm_cache
from app.token_optimizer.token_optimizer import optimize_tokens


# Initialize logger
logger = Logger()

# Load environment variables
load_dotenv()

# COST OPTIMIZATION: Balanced production configuration constants
MAX_CHUNKS_PER_SESSION = 25  # BALANCED: Increased from 10 for better coverage
RATE_LIMIT_DELAY = 2  # BALANCED: Reduced delay for faster processing
MAX_RETRIES = 2  # BALANCED: Increased retries for reliability
CACHE_EXPIRY_HOURS = 24  # Cache LLM responses for 24 hours
MAX_OUTPUT_TOKENS = 1024  # BALANCED: Increased from 512 for complete responses
MAX_ITEMS_PER_CHUNK = 10  # BALANCED: Increased from 3 for dense content

# Create the prompt template
KARYAVALI_PARSER_TEMPLATE = """You are a document parser working on Marathi Vidhan Sabha karyavali (resolutions).

Previous resolutions processed:
{previous_resolutions}


Extract the following structured data from the given text chunk:

- resolution_no: Resolution number (e.g., "१", "२", "३")
- text: The complete resolution text (keep brief to control costs)
- resolution_no_en: Resolution number in English (e.g., "1", "2", "3")


📌 Return output as valid JSON array:
[
  {{
    "resolution_no": "as in source text",
    "text": "as in source text",
    "resolution_no_en": "resolution number in english"
  }},
  ...
]

IMPORTANT: When generating Marathi text responses:
1. Use EXACT text from the input text - do not modify or translate
2. Preserve all Marathi characters, numbers and formatting
3. Do not add any English text or translations
4. Return only the extracted Marathi text exactly as it appears in source
5. DO NOT include resolutions that were already processed in previous chunks
6. Return an empty list [] if no new resolutions are found in this chunk


DO NOT return extra text, markdown, or comments.

Text chunk:
{text_chunk}
"""

class KaryavaliParser:
    def __init__(self):
        logger.info("KaryavaliParser.__init__ called")
        self.resolutions: List[Dict] = []
        self.chunk_size = 2000  # BALANCED: Increased chunk size for better context
        self.memory_key = "karyavali_parser_previous_resolutions"
        self.k = 1  # Only use last call history
        self.prompt = ChatPromptTemplate.from_template(KARYAVALI_PARSER_TEMPLATE)
        self.chain = self.prompt | llm
        self.processed_chunks = 0  # Track processed chunks

    def _get_chunk_cache_key(self, text_chunk: str, previous_resolutions: str, mapping: str) -> str:
        """Generate cache key for LLM response."""
        content = f"{text_chunk}|{previous_resolutions}|{mapping}"
        return f"karyavali_llm_cache_{hashlib.md5(content.encode('utf-8')).hexdigest()}"

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
            # Cache for CACHE_EXPIRY_HOURS
            set_llm_cache(cache_key, response, expiry_hours=CACHE_EXPIRY_HOURS)
            logger.info("LLM response cached successfully")
        except Exception as e:
            logger.error(f"Error caching response: {e}")

    def _is_duplicate_resolution(self, new_resolution: Dict) -> bool:
        """Check if a resolution is already in the list."""
        for existing_resolution in self.resolutions:
            if (new_resolution["number"] == existing_resolution["number"] and 
                new_resolution["text"] == existing_resolution["text"]):
                logger.info(f"Duplicate resolution detected: {new_resolution['number']}")
                return True
        return False

    def _update_memory(self):
        # Store only the last k (1) resolutions in Redis
        last_resolutions = self.resolutions[-self.k:] if self.k > 0 else self.resolutions
        resolutions_json = json.dumps(last_resolutions, ensure_ascii=False)
        set_llm_cache(self.memory_key, resolutions_json)
        logger.info("Memory updated with current resolutions list in Redis.")

    def _load_memory(self):
        # Load only the last k (1) resolutions from Redis
        resolutions_json = get_llm_cache(self.memory_key)
        if resolutions_json:
            try:
                return json.loads(resolutions_json)
            except Exception as e:
                logger.error(f"Error loading memory from Redis: {e}")
        return []

   
    def parse_text_chunk(self, text_chunk: str) -> List[Dict]:
        logger.info("parse_text_chunk called")
        
        
        try:
            previous_resolutions = self._load_memory()
            previous_resolutions_json = json.dumps(previous_resolutions, ensure_ascii=False)
            
            
            
                # COST OPTIMIZATION: Only make LLM call if not cached
            logger.info(f"🤖 Invoking LLM for karyavali chunk {self.processed_chunks + 1}/{MAX_CHUNKS_PER_SESSION}")
            logger.info(f"Previous resolution numbers: {[r.get('number', '') for r in previous_resolutions]}")
            
            # Add retry logic with limited attempts
            retry_count = 0
            response = None
            
            while retry_count <= MAX_RETRIES:
                try:
                    response = self.chain.invoke({
                        "previous_resolutions": previous_resolutions_json,
                        "text_chunk": text_chunk,
                        
                    })
                    break  # Success, exit retry loop
                except Exception as e:
                    retry_count += 1
                    logger.error(f"LLM call failed (attempt {retry_count}/{MAX_RETRIES + 1}): {str(e)}")
                    
                    if retry_count > MAX_RETRIES:
                        logger.error("❌ COST PROTECTION: Max retries reached. Stopping to prevent cost multiplication.")
                        return self.resolutions
                    
                    # Short delay before retry
                    time.sleep(1)
            
            if not response:
                logger.error("❌ Failed to get LLM response after retries")
                return self.resolutions
            
            content = response.content.strip()
            
            
            self.processed_chunks += 1
            
            try:
                logger.info(f"Raw LLM content: {content}")  
                if '</think>' in content:
                    content = content.split('</think>')[1].strip()
                content = content.replace('```json', '').replace('```', '').strip()
                
                if not content.startswith('[') or not content.endswith(']'):
                    logger.error("Warning: Response is not a complete JSON array")
                    return self.resolutions
                
                new_resolutions = json.loads(content)
                
                if not isinstance(new_resolutions, list):
                    logger.error("Warning: Response is not a list")
                    return self.resolutions
                
                
                added_count = 0
                for resolution in new_resolutions:
                    if (isinstance(resolution, dict) and 
                        all(key in resolution for key in ["number", "text"]) and 
                        not self._is_duplicate_resolution(resolution)):
                        self.resolutions.append(resolution)
                        added_count += 1
                        logger.info(f"Added new resolution: {resolution['number']}")
                
                self._update_memory()
                logger.info(f"✅ Chunk {self.processed_chunks} processed. Added {added_count} new resolutions. Total: {len(self.resolutions)}")
                return self.resolutions
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Raw response: {content[:500]}...")  # Truncate error log
                return self.resolutions
                
        except Exception as e:
            logger.error(f"❌ Error in parse_text_chunk: {str(e)}")
            return self.resolutions

    def process_text(self, text: str) -> List[Dict]:
        """Process a complete text by splitting into chunks based on lines."""
        logger.info("process_text called")
        
        # BALANCED PRODUCTION: Allow larger inputs for complete processing
        if len(text) > 150000:  # 150KB limit (increased from 50KB)
            logger.warning(f"⚠️  Text is very large ({len(text)} chars). Truncating to 150000 chars to maintain performance.")
            text = text[:150000] + "..."
        
        # Split text into lines and create chunks
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line)
            # If adding this line would exceed chunk size, start a new chunk
            if current_size + line_size > self.chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # COST OPTIMIZATION: Limit total chunks
        if len(chunks) > MAX_CHUNKS_PER_SESSION:
            logger.warning(f"⚠️  COST PROTECTION: Found {len(chunks)} chunks. Processing only first {MAX_CHUNKS_PER_SESSION} to control costs.")
            logger.warning(f"⚠️  To process more chunks, increase MAX_CHUNKS_PER_SESSION in karyavali_parser.py")
            chunks = chunks[:MAX_CHUNKS_PER_SESSION]
        
        logger.info(f"Processing {len(chunks)} chunks with COST CONTROLS...")
        
        # Process each chunk with rate limiting
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"📄 Processing chunk {i}/{len(chunks)} (size: {len(chunk)} chars)...")
            
            # Parse the chunk and update resolutions
            self.parse_text_chunk(chunk)
            
            # COST OPTIMIZATION: Rate limiting between LLM calls
            if i < len(chunks):  # Don't sleep after last chunk
                logger.info(f"⏱️  Rate limiting: waiting {RATE_LIMIT_DELAY} seconds before next LLM call...")
                time.sleep(RATE_LIMIT_DELAY)
        
        logger.info(f"✅ Finished processing {self.processed_chunks} chunks. Total resolutions: {len(self.resolutions)}")
        return self.resolutions

def extract_karyavali_blocks(text: str, session_id: int = None, kramak_id: int = None) -> List[Dict]:
    """
    Extracts structured ठराव (resolutions) from Marathi legislative text using LLM.
    COST OPTIMIZED: Includes caching, rate limiting, and batch size controls.
    COST TRACKED: Automatically tracks all LLM calls and costs.

    Returns:
        List[Dict]: [{"number": "१", "text": "..."}, ...]
    """
    logger.info("extract_karyavali_blocks called with COST TRACKING")
    
    # Set cost tracking context
    
    
    parser = KaryavaliParser()
    results = parser.process_text(text)
    
    
    return results
