import re
from typing import Dict
from app.logging.logger import Logger
from app.data_modals.debate import Debate

logger = Logger()

def clean_text(text: str) -> str:
    """Clean text by removing extra spaces and normalizing formatting"""
    if not text:
        return ""
    
    # Remove extra whitespace (multiple spaces, tabs, newlines)
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Handle specific corruption patterns from the logs
    # Fix "Dev     vices" -> "Devices"
    cleaned = re.sub(r'Dev\s+vices', 'Devices', cleaned)
    
    # Fix "Debat    tes" -> "Debattes"
    cleaned = re.sub(r'Debat\s+tes', 'Debattes', cleaned)
    
    # Fix "d  date" -> "date" (field name corruption)
    cleaned = re.sub(r'd\s+date', 'date', cleaned)
    
    # Fix "t   topic" -> "topic" (field name corruption)
    cleaned = re.sub(r't\s+topic', 'topic', cleaned)
    
    # Remove excessive spaces in the middle of words
    # This handles cases like "गा         ायनाने" -> "गायनाने"
    cleaned = re.sub(r'(\w)\s+(\w)', r'\1\2', cleaned)
    
    # Normalize common OCR artifacts
    cleaned = re.sub(r' +', ' ', cleaned)  # Multiple spaces to single space
    cleaned = re.sub(r'\.+', '.', cleaned)  # Multiple dots to single dot
    
    return cleaned.strip()

def clean_list(items: list) -> list:
    """Clean a list of strings by removing extra spaces"""
    if not items:
        return []
    return [clean_text(item) for item in items if item and clean_text(item)]

def validate_debate_data(debate: Dict) -> Dict:
    """Validate and clean debate data before database insertion"""
    cleaned_debate = {}
    
    # Clean text fields
    cleaned_debate['topic'] = clean_text(debate.get('topic', ''))
    cleaned_debate['text'] = clean_text(debate.get('text', ''))
    cleaned_debate['document_name'] = clean_text(debate.get('document_name', ''))
    cleaned_debate['kramank_id'] = clean_text(debate.get('kramank_id', ''))
    
    # Clean list fields
    cleaned_debate['members'] = clean_list(debate.get('members', []))
    cleaned_debate['image_name'] = clean_list(debate.get('image_name', []))
    
    # Clean other fields
    cleaned_debate['lob_type'] = clean_text(debate.get('lob_type', ''))
    cleaned_debate['lob'] = clean_text(debate.get('lob', ''))
    cleaned_debate['sub_lob'] = clean_text(debate.get('sub_lob', ''))
    cleaned_debate['question_by'] = clean_text(debate.get('question_by', ''))
    cleaned_debate['answer_by'] = clean_text(debate.get('answer_by', ''))
    cleaned_debate['ministry'] = clean_text(debate.get('ministry', ''))
    cleaned_debate['place'] = clean_text(debate.get('place', ''))
    
    # Validate required fields
    if not cleaned_debate['topic']:
        logger.warning("⚠️ Empty topic found, using default")
        cleaned_debate['topic'] = "Unknown Topic"
    
    if not cleaned_debate['document_name']:
        cleaned_debate['document_name'] = f"{cleaned_debate['topic']}_Document"
    
    return cleaned_debate

def extract_fields(debate: Dict, debate_type: Dict):
    """
    Extract key fields from OCR text based on debate type using regex templates.
    Returns a dict of extracted fields.
    """
    # Clean and validate debate data first
    cleaned_debate = validate_debate_data(debate)
    
    # Extract fields from the Marathi text
    if debate_type.get("lob_type") == "Devices":
        debate_data = extract_fields_from_devices(cleaned_debate['text'])
    elif debate_type.get("lob_type") == "Others":
        debate_data = extract_fields_from_others(cleaned_debate['text'])
    else:
        debate_data = extract_fields_from_devices(cleaned_debate['text'])
    
    # Clean extracted data
    if debate_data.get("date"):
        debate_data["date"] = clean_text(debate_data["date"])
    if debate_data.get("members"):
        debate_data["members"] = clean_list(debate_data["members"])
    if debate_data.get("answers_by"):
        debate_data["answers_by"] = clean_list(debate_data["answers_by"])
    if debate_data.get("question_number"):
        debate_data["question_number"] = [clean_text(str(q)) for q in debate_data["question_number"] if q]
    
    # Prepare Debate data modal object
    try:
        debate_obj = Debate(
            debate_id=None,
            document_name=cleaned_debate.get('document_name'),
            kramank_id=cleaned_debate.get('kramank_id'),
            date=debate_data.get("date"),
            members=debate_data.get("members", []),
            lob_type=clean_text(debate_type.get("lob_type")) if debate_type else None,
            lob=clean_text(debate_type.get("lob")) if debate_type else None,
            sub_lob=clean_text(debate_type.get("sub_lob")) if debate_type else None,
            question_no=debate_data.get("question_number", [None])[0] if debate_data.get("question_number") else None,
            question_by=None,  # Could be extracted if available
            answer_by=debate_data.get("answers_by", [None])[0] if debate_data.get("answers_by") else None,
            ministry=None,  # Could be extracted if available
            topic=cleaned_debate.get("topic", ""),
            text=cleaned_debate.get("text", ""),
            image_name=cleaned_debate.get("image_name", []),
            place=cleaned_debate.get("place")
        )
        
        logger.info(f"✅ Created debate object with topic: {debate_obj.topic[:50]}...")
        logger.info(f"📊 Debate stats: text_length={len(debate_obj.text)}, members={len(debate_obj.members)}")
        
        return debate_obj
        
    except Exception as e:
        logger.error(f"❌ Error creating debate object: {str(e)}")
        logger.error(f"Debate data: {cleaned_debate}")
        return None

def extract_fields_from_debates(text):
    data = {}
    # 1. Date
    date_match = re.search(r'\d{1,2} [ज|फ|म|ए|म|ज|ज|ऑ|स|ऑ|नो|ड][^\s]* \d{4}', text)
    data["date"] = date_match.group() if date_match else None
    return data

def extract_fields_from_others(text):
    data = {}
    # 1. Date
    date_match = re.search(r'\d{1,2} [ज|फ|म|ए|म|ज|ज|ऑ|स|ऑ|नो|ड][^\s]* \d{4}', text)
    data["date"] = date_match.group() if date_match else None

    members_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? [^\n:,]+'
    members = re.findall(members_pattern, text)
    data["members"] = list(set(members))  # unique

    return data

def extract_fields_from_devices(text):
    data = {}
    # 1. Date
    date_match = re.search(r'\d{1,2} [ज|फ|म|ए|म|ज|ज|ऑ|स|ऑ|नो|ड][^\s]* \d{4}', text)
    data["date"] = date_match.group() if date_match else None

    # 2. Question numbers
    question_numbers = re.findall(r'(?:प्रश्न क्रमांक|क्रमांक)\s*(\d+)', text)
    data["question_number"] = question_numbers

    # 3. Members
    members_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? [^\n:,]+'
    members = re.findall(members_pattern, text)
    data["members"] = list(set(members))  # unique

    # 4. Topics
    topics = []
    topic_lines = text.split('\n')
    for line in topic_lines:
        if "वेतन" in line or "अनुदान" in line or "नेमणूक" in line:
            topics.append(line.strip())
    data["topics"] = list(set(topics))

    # 5. Answers by (look for names followed by colon)
    answers_by = re.findall(r'(?:श्री\.|श्रीमती\.?)\s[^\n:]+(?= :|\:)', text)
    data["answers_by"] = list(set(answers_by))

    return data