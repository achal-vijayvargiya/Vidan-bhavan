import json
from pathlib import Path
from app.config.OpenRouter import llm
import re
import json as pyjson
from app.logging.logger import Logger

logger = Logger()

# Load lob_master.json (Marathi LOB master data)
lob_master_path = Path(__file__).parent.parent / "master_data" / "lob_master.json"
with open(lob_master_path, encoding="utf-8") as f:
    LOB_MASTER = json.load(f)
logger.info(f"LOB_MASTER: {LOB_MASTER}")



# Prepare a list of all lob and sub_lob items for matching
LOB_ITEMS = []
for entry in LOB_MASTER:
    lob = entry["lob"]
    LOB_ITEMS.append(lob)
    for sub in entry.get("sub_lob", []):
        LOB_ITEMS.append(sub)

def identify_debate_type(debate_topic):
    """
    Identify the LOB item for a given debate topic (Marathi) using LLM and lob_master.json.
    Returns the best matching lob item (lob, sub_lob, lob_type).
    """
    # Prepare prompt for LLM
    prompt = f"""
You are an expert in Indian legislative procedures. Given a debate topic in Marathi, match it to the most appropriate item from the following LOB master list. Return the best matching lob, sub_lob (if any), and lob_type as JSON.

Debate topic: "{debate_topic}"

LOB master data (JSON):
{json.dumps(LOB_MASTER, ensure_ascii=False, indent=2)}

Respond with a JSON object with keys: lob, sub_lob, lob_type. If no sub_lob matches, set sub_lob to an empty string.

Return Json format:
{{
    "lob": "string",
    "sub_lob": "string",
    "lob_type": "string"
}}

If you cannot confidently classify the debate topic, return the following default JSON:
{{
    "lob": "{debate_topic}",
    "sub_lob": "none",
    "lob_type": "others"
}}


"""
    
    # LLM call
    response = llm.invoke(prompt)
    # Try to parse JSON from LLM response
    logger.info(f"response lob: {response}")
    try:
        # Extract JSON from response, removing unwanted text like ```json and ```
        content = str(response.content)
        # Remove code block markers if present
        if '</think>' in content:
                content = content.split('</think>')[1].strip()
        content = content.replace('```json', '').replace('```', '').strip()
        # Try to find the first JSON object in the string
        # Find all JSON objects in the string, not just the first
        matches = re.findall(r'\{[\s\S]+?\}', content)
        logger.info(f"matches: {matches}")
        if matches:
            result = pyjson.loads(matches[0])
            return result
        # If no match, try to parse the cleaned content directly
        result = pyjson.loads(content)
        return result
    except Exception as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return None 