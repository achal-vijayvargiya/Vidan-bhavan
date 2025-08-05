from langchain.prompts import ChatPromptTemplate
import json
from dotenv import load_dotenv
from app.config.OpenRouter import llm
import time
import re
from app.logging.logger import Logger

# Initialize logger
logger = Logger()

# Load environment variables
load_dotenv()

# Create the prompt template
DEBATE_PARSER_TEMPLATE = """You are a document parser working on Marathi Vidhan Sabha debates.

Extract the following structured data from the given debate text:

- date: (e.g., "१३ मार्च २०००")
- question_number(s): (e.g., [45, 46])
- members: list of names involved (asking or speaking)
- topics: key issues or bill subjects
- answers_by: list of names who responded (with or without colon)

📌 Return output as valid JSON:
{{
  "date": "",
  "question_number": [],
  "members": [],
  "topics": [],
  "answers_by": []
}}
IMPORTANT: When generating Marathi text responses:
1. Use EXACT text from the input text - do not modify or translate
2. Preserve all Marathi characters, numbers and formatting
3. Do not add any English text or translations
4. Return only the extracted Marathi text exactly as it appears in source

DO NOT return extra text, markdown, or comments.

Text:
{text}

DO NOT return extra text, markdown, or comments.

"""

prompt = ChatPromptTemplate.from_template(DEBATE_PARSER_TEMPLATE)

# Create the chain
chain = prompt | llm

def get_debate_data(text) -> dict:
    logger.info("get_debate_data called")
    try:
        logger.info("Invoking LLM for debate data extraction")
        result = chain.invoke({"text": text})
        
        # Check if result and content exist
        if not result or not hasattr(result, 'content'):
            logger.error("Error: Invalid response from LLM")
            return None
            
        # Clean the response content
        content = result.content.strip()
        logger.info(f"Raw LLM content: {content}")
        content = re.sub(r'^```(?:json)?\s*|\s*```$','', content.strip(), flags=re.MULTILINE)
        # Try to find JSON content if it's wrapped in other text
        try:
            # First try direct JSON parsing
            extracted_data = json.loads(content)
            logger.info(f"Successfully parsed JSON from LLM content.")
        except json.JSONDecodeError:
            logger.error("Direct JSON parsing failed, attempting regex extraction.")
            # If that fails, try to extract JSON from the text
            json_match = re.search(r'\{.*?\}', content, re.DOTALL)
            if json_match:
                try:
                    extracted_data = json.loads(json_match.group())
                    logger.info("Successfully parsed JSON from regex extraction.")
                except json.JSONDecodeError:
                    logger.error(f"Error: Could not parse JSON from response: {json_match.group()}")
                    return None
            else:
                logger.error(f"Error: No JSON found in response: {content}")
                return None
        
        # Validate the extracted data structure
        required_fields = ["date", "question_number", "members", "topics", "answers_by"]
        if not all(field in extracted_data for field in required_fields):
            logger.error(f"Error: Missing required fields in response. Got: {list(extracted_data.keys())}")
            return None
            
        time.sleep(2)  # Rate limiting
        logger.info("Debate data extraction successful.")
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error processing debate data: {str(e)}")
        return None
