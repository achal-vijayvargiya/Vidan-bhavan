from langchain.prompts import ChatPromptTemplate
import json
from dotenv import load_dotenv
from app.config.OpenRouter import llm, llm_gemini
import time
from typing import List, Dict, Optional
from langchain.memory import ConversationBufferMemory
from app.logging.logger import Logger
from app.database.redis_cache import get_llm_cache, set_llm_cache, delete_llm_cache
from app.token_optimizer.token_optimizer import optimize_tokens

# Initialize logger
logger = Logger()

# Load environment variables
load_dotenv()

# Create the prompt template
INDEX_PARSER_TEMPLATE = """You are a document parser working on Marathi Vidhan Sabha index/table of contents information.

Previous data processed:
{previous_data}

A mapping for token compression is provided below. Before extracting data, first decompress the text chunk by replacing numbers with their corresponding words from the mapping:
{mapping}

Extract the following structured data from the given Marathi text chunk:

1. **Date Information**: Look for dates in formats like "दिनांक", "तारीख", numerical dates
2. **Khand (खंड/Section)**: Look for section numbers like "खंड १", "खंड २", etc.
3. **Members**: Names of members mentioned in the index
4. **Resolutions**: Resolution numbers, titles, and descriptions for the day

📌 Return output as valid JSON object:
{{
  "date": "extracted date in Marathi",
  "khand": "section number/name",
  "members": [
    {{
      "name": "member name in Marathi",
      "role": "role/position if mentioned"
    }}
  ],
  "resolutions": [
    {{
      "resolution_no": "resolution number",
      "title": "resolution title in Marathi",
      "description": "brief description if available",
      "page_no": "page number if mentioned"
    }}
  ]
}}

IMPORTANT: When generating Marathi text responses:
1. Use EXACT text from the input text - do not modify or translate
2. Preserve all Marathi characters, numbers and formatting
3. Do not add any English text or translations
4. Return only the extracted Marathi text exactly as it appears in source
5. DO NOT include data that was already processed in previous chunks
6. Return empty arrays [] for members and resolutions if none found
7. Return null for date and khand if not found

DO NOT return extra text, markdown, or comments.

Text chunk:
{text_chunk}
"""

class IndexDataExtractor:
    def __init__(self):
        logger.info("IndexDataExtractor.__init__ called")
        self.extracted_data = {
            "date": None,
            "khand": None,
            "members": [],
            "resolutions": []
        }
        self.chunk_size = 3000
        self.memory_key = "index_parser_previous_data"
        self.k = 1  # Only use last call history
        self.prompt = ChatPromptTemplate.from_template(INDEX_PARSER_TEMPLATE)
        self.chain = self.prompt | llm_gemini

    def _is_duplicate_member(self, new_member: Dict) -> bool:
        """Check if member already exists"""
        for existing_member in self.extracted_data["members"]:
            if new_member["name"] == existing_member["name"]:
                logger.info(f"Duplicate member detected: {new_member['name']}")
                return True
        return False

    def _is_duplicate_resolution(self, new_resolution: Dict) -> bool:
        """Check if resolution already exists"""
        for existing_resolution in self.extracted_data["resolutions"]:
            if new_resolution["resolution_no"] == existing_resolution["resolution_no"]:
                logger.info(f"Duplicate resolution detected: {new_resolution['resolution_no']}")
                return True
        return False

    def _update_memory(self):
        """Store extracted data in Redis for context"""
        # Store summary of extracted data for next chunk
        summary_data = {
            "date": self.extracted_data["date"],
            "khand": self.extracted_data["khand"],
            "member_names": [m["name"] for m in self.extracted_data["members"][-self.k:]],
            "resolution_nos": [r["resolution_no"] for r in self.extracted_data["resolutions"][-self.k:]]
        }
        data_json = json.dumps(summary_data, ensure_ascii=False)
        set_llm_cache(self.memory_key, data_json)
        logger.info("Memory updated with current extracted data in Redis.")

    def _load_memory(self):
        """Load previously extracted data from Redis"""
        data_json = get_llm_cache(self.memory_key)
        if data_json:
            try:
                return json.loads(data_json)
            except Exception as e:
                logger.error(f"Error loading memory from Redis: {e}")
        return {}

    def parse_text_chunk(self, text_chunk: str) -> Dict:
        """Parse a single text chunk and extract structured data"""
        logger.info("parse_text_chunk called for index data")
        try:
            previous_data = self._load_memory()
            previous_data_json = json.dumps(previous_data, ensure_ascii=False)
            
            # Optimize tokens in the text chunk
            optimized_text, mapping = optimize_tokens(text_chunk)
            mapping_json = json.dumps(mapping, ensure_ascii=False)
            
            logger.info(f"Invoking LLM for index chunk. Previous data: {previous_data_json}")
            
            response = self.chain.invoke({
                "previous_data": previous_data_json,
                "text_chunk": optimized_text,
                "mapping": mapping_json
            })
            
            try:
                content = response.content.strip()
                logger.info(f"Raw LLM content: {content}")
                
                # Clean up the response
                content = content.replace('```json', '').replace('```', '').strip()
                
                if not content.startswith('{') or not content.endswith('}'):
                    logger.error("Warning: Response is not a complete JSON object")
                    return self.extracted_data
                
                chunk_data = json.loads(content)
                
                if not isinstance(chunk_data, dict):
                    logger.error("Warning: Response is not a dictionary")
                    return self.extracted_data
                
                # Merge extracted data
                self._merge_chunk_data(chunk_data)
                
                # Update memory
                self._update_memory()
                
                logger.info(f"parse_text_chunk finished. Total members: {len(self.extracted_data['members'])}, resolutions: {len(self.extracted_data['resolutions'])}")
                return self.extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response: {e}")
                logger.error(f"Raw response: {response.content}")
                return self.extracted_data
                
        except Exception as e:
            logger.error(f"Error in parse_text_chunk: {str(e)}")
            return self.extracted_data

    def _merge_chunk_data(self, chunk_data: Dict):
        """Merge data from current chunk with accumulated data"""
        # Update date if found and not already set
        if chunk_data.get("date") and not self.extracted_data["date"]:
            self.extracted_data["date"] = chunk_data["date"]
            logger.info(f"Date extracted: {chunk_data['date']}")
        
        # Update khand if found and not already set
        if chunk_data.get("khand") and not self.extracted_data["khand"]:
            self.extracted_data["khand"] = chunk_data["khand"]
            logger.info(f"Khand extracted: {chunk_data['khand']}")
        
        # Add new members
        if chunk_data.get("members") and isinstance(chunk_data["members"], list):
            for member in chunk_data["members"]:
                if (isinstance(member, dict) and 
                    "name" in member and 
                    not self._is_duplicate_member(member)):
                    self.extracted_data["members"].append(member)
                    logger.info(f"Added new member: {member['name']}")
        
        # Add new resolutions
        if chunk_data.get("resolutions") and isinstance(chunk_data["resolutions"], list):
            for resolution in chunk_data["resolutions"]:
                if (isinstance(resolution, dict) and 
                    "resolution_no" in resolution and 
                    not self._is_duplicate_resolution(resolution)):
                    self.extracted_data["resolutions"].append(resolution)
                    logger.info(f"Added new resolution: {resolution['resolution_no']}")

    def process_text(self, text: str) -> Dict:
        """Process the entire text by breaking it into chunks"""
        logger.info("process_text called for index data extraction")
        
        # Split text into lines and create chunks
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
        
        logger.info(f"Processing {len(chunks)} chunks for index data...")
        
        # Process each chunk
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}...")
            logger.info(f"Chunk size: {len(chunk)} characters")
            self.parse_text_chunk(chunk)
            logger.info(f"Current data: date={self.extracted_data['date']}, khand={self.extracted_data['khand']}, members={len(self.extracted_data['members'])}, resolutions={len(self.extracted_data['resolutions'])}")
            time.sleep(2)  # Rate limiting
        
        logger.info(f"Finished processing all chunks. Final data: {json.dumps(self.extracted_data, ensure_ascii=False, indent=2)}")
        return self.extracted_data

    def clear_memory(self):
        """Clear the memory cache"""
        delete_llm_cache(self.memory_key)
        logger.info("Index parser memory cleared")

def extract_index_data(ocr_results_index: dict) -> Dict:
    """Main function to extract index data from Marathi OCR text"""
    logger.info("extract_index_data called")
    extractor = IndexDataExtractor()
    text = "\n".join([page_ocr['text'] for page_ocr in ocr_results_index])
    return extractor.process_text(text)
