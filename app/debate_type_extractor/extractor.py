import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict
from functools import lru_cache
from google.cloud import vision
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from app.ocr.vision_ocr import setup_vision_client

# Load environment variables
load_dotenv()

# Configure Google Generative AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set. Please set it in your .env file")

genai.configure(api_key=GOOGLE_API_KEY)

# COST OPTIMIZATION: Configuration constants
MAX_BATCH_SIZE = 5  # Process max 5 files at a time
RATE_LIMIT_DELAY = 2  # 2 seconds between batches
MAX_OUTPUT_TOKENS = 512  # Limit token generation
REQUEST_TIMEOUT = 30  # Timeout for API calls
MAX_RETRIES = 2  # Limit retry attempts

class DebateType(BaseModel):
    type: str = Field(description="The type of debate in Marathi")
    explanation: str = Field(description="Explanation of the debate type in Marathi")

class DebateTypeList(BaseModel):
    debate_types: List[DebateType]

# COST OPTIMIZATION: Add caching to prevent repeated LLM calls
@lru_cache(maxsize=1000)
def _cached_analyze_debate_types(text_hash: str, text: str) -> str:
    """Cached version of debate type analysis to avoid repeated API calls."""
    return _analyze_debate_types_internal(text)

def _get_text_hash(text: str) -> str:
    """Generate hash for text to use as cache key."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using Google Cloud Vision OCR."""
    client = setup_vision_client()
    
    try:
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f'Error in OCR: {response.error.message}')
        
        if not response.full_text_annotation:
            print(f"Warning: No text detected in {image_path}")
            return ""
            
        return response.full_text_annotation.text
        
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return ""

def _analyze_debate_types_internal(text: str) -> str:
    """Internal method for LLM analysis with cost controls."""
    if not text.strip():
        raise ValueError("No text provided for analysis")
    
    try:
        # COST OPTIMIZATION: Initialize model with token limits
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # COST OPTIMIZATION: Configure generation limits
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.3,
        )
        
        # Create the prompt with explicit JSON formatting instructions
        prompt = f"""You are an expert in analyzing Marathi legislative debates. 
        Analyze the following text from Maharashtra Vidhan Bhavan and identify unique types of debates.
        For each type, provide a brief explanation in Marathi.
        Focus on identifying formal debate types like तारांकित प्रश्न, लक्षवेधी सूचना, etc.
        
        IMPORTANT: Keep responses concise to control costs. Maximum 3-5 debate types.
        
        Text to analyze:
        {text[:2000]}...  # COST OPTIMIZATION: Limit input text length
        
        IMPORTANT: You must respond with a valid JSON object in exactly this format:
        {{
            "debate_types": [
                {{
                    "type": "debate type in Marathi",
                    "explanation": "brief explanation in Marathi"
                }}
            ]
        }}
        
        Do not include any other text or explanation outside the JSON object.
        Ensure the JSON is properly formatted with double quotes for all keys and string values.
        """
        
        # COST OPTIMIZATION: Generate response with limits and timeout
        response = model.generate_content(
            prompt, 
            generation_config=generation_config,
            request_options={"timeout": REQUEST_TIMEOUT}
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"Error in model response: {str(e)}")
        raise Exception(f"Error in analyzing debate types: {str(e)}")

def analyze_debate_types(text: str) -> List[Dict]:
    """Analyze the extracted text to identify debate types using Google's Generative AI with caching."""
    if not text.strip():
        raise ValueError("No text provided for analysis")
    
    # COST OPTIMIZATION: Use cached version to avoid repeated API calls
    text_hash = _get_text_hash(text)
    
    try:
        # Check cache first
        response_text = _cached_analyze_debate_types(text_hash, text)
        
        # Clean the response text
        response_text = response_text.strip()
        
        # Try to find JSON in the response
        try:
            # First try direct JSON parsing
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    print("Raw response:", response_text)
                    raise Exception("Could not parse JSON from model response")
            else:
                print("Raw response:", response_text)
                raise Exception("No JSON object found in model response")
        
        # Validate the result structure
        if not isinstance(result, dict) or 'debate_types' not in result:
            print("Raw response:", response_text)
            raise Exception("Response does not contain 'debate_types' key")
            
        debate_types = result.get('debate_types', [])
        if not isinstance(debate_types, list):
            raise Exception("'debate_types' is not a list")
            
        # Validate each debate type
        for dt in debate_types:
            if not isinstance(dt, dict):
                raise Exception("Debate type is not a dictionary")
            if 'type' not in dt or 'explanation' not in dt:
                raise Exception("Debate type missing required fields")
            if not isinstance(dt['type'], str) or not isinstance(dt['explanation'], str):
                raise Exception("Debate type fields must be strings")
        
        return debate_types
            
    except Exception as e:
        print(f"Error in analyzing debate types: {str(e)}")
        # COST OPTIMIZATION: Don't retry on errors to prevent cost multiplication
        raise Exception(f"Error in analyzing debate types: {str(e)}")

def extract_debate_types_from_folder(folder_path: str) -> List[Dict]:
    """
    Extract and analyze debate types from a folder containing debate images.
    COST OPTIMIZED: Implements batching, caching, and error handling.
    
    Args:
        folder_path (str): Path to the folder containing debate images
        
    Returns:
        List[Dict]: List of dictionaries containing debate types and explanations
    """
    try:
        # Validate folder path
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
        image_files = [f for f in folder.glob('*') if f.suffix.lower() in image_extensions]
        
        if not image_files:
            raise ValueError(f"No image files found in {folder_path}")
        
        # COST OPTIMIZATION: Limit batch size to prevent mass API calls
        if len(image_files) > MAX_BATCH_SIZE:
            print(f"⚠️  WARNING: Found {len(image_files)} files. Processing only first {MAX_BATCH_SIZE} to control costs.")
            print(f"⚠️  To process more files, increase MAX_BATCH_SIZE in the code and run again.")
            image_files = image_files[:MAX_BATCH_SIZE]
        
        print(f"Found {len(image_files)} image files to process")
        
        # Extract text from images with rate limiting
        all_text = []
        successful_extractions = 0
        
        for i, image_file in enumerate(image_files):
            try:
                print(f"Processing {i+1}/{len(image_files)}: {image_file.name}")
                
                text = extract_text_from_image(str(image_file))
                if text.strip():
                    all_text.append(text)
                    successful_extractions += 1
                    print(f"✅ Successfully extracted text from {image_file.name}")
                else:
                    print(f"⚠️  No text extracted from {image_file.name}")
                
                # COST OPTIMIZATION: Rate limiting between files
                if i < len(image_files) - 1:  # Don't sleep after last file
                    time.sleep(RATE_LIMIT_DELAY)
                    
            except Exception as e:
                print(f"❌ Warning: Could not process {image_file}: {str(e)}")
                continue  # COST OPTIMIZATION: Continue processing other files
        
        if not all_text:
            raise ValueError("No text could be extracted from any images")
        
        print(f"✅ Successfully extracted text from {successful_extractions}/{len(image_files)} files")
        
        # Combine all text
        combined_text = "\n".join(all_text)
        print(f"Total extracted text length: {len(combined_text)} characters")
        
        # COST OPTIMIZATION: Truncate very long text to control input costs
        if len(combined_text) > 10000:
            print(f"⚠️  Text is very long ({len(combined_text)} chars). Truncating to 10000 chars to control costs.")
            combined_text = combined_text[:10000] + "..."
        
        # Analyze debate types with caching
        print("🤖 Analyzing debate types with LLM...")
        debate_types = analyze_debate_types(combined_text)
        print(f"✅ Found {len(debate_types)} debate types")
        
        # Create outputs directory if it doesn't exist
        outputs_dir = Path("outputs")
        outputs_dir.mkdir(exist_ok=True)
        
        # Save results to JSON file
        date_str = folder.name
        output_file = outputs_dir / f"debate_types_{date_str}.json"
        output_file_text = outputs_dir / f"fulltext_{date_str}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(debate_types, f, ensure_ascii=False, indent=2)
        with open(output_file_text, 'w', encoding='utf-8') as f:
            f.write(combined_text)
        
        print(f"💾 Results saved to {output_file}")
        return debate_types
        
    except Exception as e:
        print(f"❌ Error in extract_debate_types_from_folder: {str(e)}")
        raise Exception(f"Error in extract_debate_types_from_folder: {str(e)}") 