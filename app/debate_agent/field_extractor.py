import re
from typing import Dict
from app.logging.logger import Logger
from app.data_modals.debate import Debate
from app.debate_parser.llm_parser import get_debate_data
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
    
    # Remove excessive spaces in the middle of words ONLY for specific OCR artifacts
    # This is more targeted to avoid removing legitimate spaces between words
    # Only fix cases where there are 3+ spaces between characters that are likely part of the same word
    cleaned = re.sub(r'(\w)\s{3,}(\w)', r'\1\2', cleaned)
    
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
    
    # Ensure sequence number is present
    if 'sequence_number' not in debate:
        logger.error("❌ Sequence number is required but not provided")
        raise ValueError("Sequence number is required")
    
    # Clean text fields
    cleaned_debate['topic'] = clean_text(debate.get('topic', ''))
    cleaned_debate['text'] = clean_text(debate.get('text', ''))
    cleaned_debate['document_name'] = clean_text(debate.get('document_name', ''))
    cleaned_debate['kramank_id'] = clean_text(debate.get('kramank_id', ''))
    
    # Copy required fields
    cleaned_debate['sequence_number'] = debate['sequence_number']  # Already validated
    cleaned_debate['vol'] = debate.get('vol')
    cleaned_debate['chairman'] = debate.get('chairman')
    
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
    debate_data = extract_fields_llm(cleaned_debate['text'])
    # Extract fields from the Marathi text
    # if debate_type.get("lob_type") == "Devices":
    #     debate_data = extract_fields_from_devices(cleaned_debate['text'])
    # elif debate_type.get("lob_type") == "Others":
    #     debate_data = extract_fields_from_others(cleaned_debate['text'])
    # else:
    #     debate_data = extract_fields_from_devices(cleaned_debate['text'])
    
    # Clean extracted data
    if debate_data.get("date"):
        debate_data["date"] = clean_text(debate_data["date"])
    if debate_data.get("members"):
        debate_data["members"] = clean_list(debate_data["members"])
    if debate_data.get("answers_by"):
        debate_data["answers_by"] = clean_list(debate_data["answers_by"])
    if debate_data.get("question_by"):
        debate_data["question_by"] = clean_list(debate_data["question_by"])
    if debate_data.get("question_number"):
        debate_data["question_number"] = [clean_text(str(q)) for q in debate_data["question_number"] if q]
    if debate_data.get("title"):
        debate_data["title"] = clean_text(debate_data["title"])
    else:
        debate_data["title"] = cleaned_debate.get("title", cleaned_debate.get("topic", ""))
    
    # Ensure topic is always set and not empty
    if debate_data.get("topic"):
        debate_data["topic"] = clean_text(debate_data["topic"])
    else:
        debate_data["topic"] = cleaned_debate.get("topic", "Unknown Topic")
    
    # Final validation to ensure topic is never empty
    if not debate_data["topic"] or debate_data["topic"].strip() == "":
        debate_data["topic"] = "Unknown Topic"
    if debate_data.get("question_by"):
        debate_data["question_by"] = clean_list(debate_data["question_by"])
    if debate_data.get("topics"):
        debate_data["topics"] = clean_list(debate_data["topics"])

    # Final validation to ensure required fields are not empty
    if not debate_data.get("topic") or debate_data["topic"].strip() == "":
        logger.warning("⚠️ Topic is empty after extraction, using default")
        debate_data["topic"] = "Unknown Topic"
    
    if not debate_data.get("title") or debate_data["title"].strip() == "":
        logger.warning("⚠️ Title is empty after extraction, using topic as title")
        debate_data["title"] = debate_data["topic"]
    
    # Create comprehensive member categorization
    all_members = set()
    question_initiators = set()
    answer_providers = set()
    
    # Add question initiators
    if debate_data.get("question_by"):
        for member in debate_data["question_by"]:
            all_members.add(member)
            question_initiators.add(member)
    
    # Add answer providers
    if debate_data.get("answers_by"):
        for member in debate_data["answers_by"]:
            all_members.add(member)
            answer_providers.add(member)
    
    # Add other members mentioned
    if debate_data.get("members"):
        for member in debate_data["members"]:
            all_members.add(member)
    
    # Convert sets to lists for database storage
    all_members_list = list(all_members)
    question_initiators_list = list(question_initiators)
    answer_providers_list = list(answer_providers)
    
    # Log member categorization for debugging
    logger.info(f"👥 Member categorization:")
    logger.info(f"   Question initiators: {question_initiators_list}")
    logger.info(f"   Answer providers: {answer_providers_list}")
    logger.info(f"   Total unique members: {len(all_members_list)}")
    
    # Debug logging
    logger.info(f"🔍 Final topic: '{debate_data.get('topic', 'NOT_SET')}'")
    logger.info(f"🔍 Final title: '{debate_data.get('title', 'NOT_SET')}'")

    # Prepare Debate data modal object
    try:
        debate_obj = Debate(
            debate_id=None,
            document_name=cleaned_debate.get('document_name'),
            kramank_id=cleaned_debate.get('kramank_id'),
            date=debate_data.get("date"),
            members=all_members_list,  # All members mentioned in the debate
            lob_type=clean_text(debate_type.get("lob_type")) if debate_type else None,
            lob=clean_text(debate_type.get("lob")) if debate_type else None,
            sub_lob=clean_text(debate_type.get("sub_lob")) if debate_type else None,
            question_no=debate_data.get("question_number", [None])[0] if debate_data.get("question_number") else None,
            question_by=", ".join(question_initiators_list) if question_initiators_list else None,  # Who initiated the topic
            answer_by=", ".join(answer_providers_list) if answer_providers_list else None,  # Who answered
            ministry=None,  # Could be extracted if available
            title=debate_data.get("title",""),
            topic=debate_data.get("topic",""),
            text=cleaned_debate.get("text", ""),
            image_name=cleaned_debate.get("image_name", []),
            place=cleaned_debate.get("place"),
            sequence_number=debate.get("sequence_number"),  # Add sequence number
            vol=debate.get("vol"),  # Add volume
            chairman=debate.get("chairman")  # Add chairman
        )
        
        logger.info(f"✅ Created debate object with topic: {debate_obj.topic[:50]}...")
        logger.info(f"📊 Debate stats: text_length={len(debate_obj.text)}, members={len(debate_obj.members)}")
        logger.info(f"🔍 Question by: {debate_obj.question_by}")
        logger.info(f"🔍 Answer by: {debate_obj.answer_by}")
        
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

    # 2. Enhanced member role identification
    # Pattern for question initiators (people who ask questions)
    question_initiators_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)(?:\s+यांनी|\s+ने|\s+कडून)?\s+(?:प्रश्न\s+विचारला|चर्चा\s+सुरू\s+केली|विषय\s+मांडला|प्रश्न\s+केला)'
    question_initiators = re.findall(question_initiators_pattern, text)
    data["question_by"] = list(set(question_initiators)) if question_initiators else []
    
    # Pattern for answer providers (ministers, officials who respond)
    answer_providers_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)(?:\s+यांनी|\s+ने|\s+कडून)?\s+(?:उत्तर\s+दिले|जबाब\s+दिला|स्पष्टीकरण\s+दिले|माहिती\s+दिली)'
    answer_providers = re.findall(answer_providers_pattern, text)
    data["answers_by"] = list(set(answer_providers)) if answer_providers else []
    
    # General members pattern (all names mentioned)
    members_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? [^\n:,]+'
    members = re.findall(members_pattern, text)
    data["members"] = list(set(members))  # unique

    # 3. Additional patterns for question initiators
    additional_question_patterns = [
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+यांनी\s+प्रश्न\s+विचारला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+कडून\s+प्रश्न\s+आला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+ने\s+चर्चा\s+सुरू\s+केली'
    ]
    
    for pattern in additional_question_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in data["question_by"]:
                data["question_by"].append(match)
    
    # 4. Additional patterns for answer providers
    additional_answer_patterns = [
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+यांनी\s+उत्तर\s+दिले',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+कडून\s+जबाब\s+आला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+ने\s+स्पष्टीकरण\s+दिले'
    ]
    
    for pattern in additional_answer_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in data["answers_by"]:
                data["answers_by"].append(match)
    
    # Remove duplicates
    data["question_by"] = list(set(data["question_by"]))
    data["answers_by"] = list(set(data["answers_by"]))

    return data
def extract_fields_llm(text):
    """
    Extract fields from debate text using the LLM parser.
    """
    
    data = get_debate_data(text)
    if not data:
        logger.error("❌ LLM extraction failed or returned no data.")
        return {}

    # Optionally, clean or post-process data here if needed
    return data

def extract_fields_from_devices(text):
    data = {}
    # 1. Date
    date_match = re.search(r'\d{1,2} [ज|फ|म|ए|म|ज|ज|ऑ|स|ऑ|नो|ड][^\s]* \d{4}', text)
    data["date"] = date_match.group() if date_match else None

    # 2. Question numbers
    question_numbers = re.findall(r'(?:प्रश्न क्रमांक|क्रमांक)\s*(\d+)', text)
    data["question_number"] = question_numbers

    # 3. Members - Enhanced pattern matching for different roles
    # Pattern for question initiators (people who ask questions)
    question_initiators_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)(?:\s+यांनी|\s+ने|\s+कडून)?\s+(?:प्रश्न\s+विचारला|चर्चा\s+सुरू\s+केली|विषय\s+मांडला|प्रश्न\s+केला)'
    question_initiators = re.findall(question_initiators_pattern, text)
    data["question_by"] = list(set(question_initiators)) if question_initiators else []
    
    # Pattern for answer providers (ministers, officials who respond)
    answer_providers_pattern = r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)(?:\s+यांनी|\s+ने|\s+कडून)?\s+(?:उत्तर\s+दिले|जबाब\s+दिला|स्पष्टीकरण\s+दिले|माहिती\s+दिली)'
    answer_providers = re.findall(answer_providers_pattern, text)
    data["answers_by"] = list(set(answer_providers)) if answer_providers else []
    
    # General members pattern (all names mentioned)
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

    # 5. Additional patterns for question initiators
    # Look for names followed by question-related phrases
    additional_question_patterns = [
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+यांनी\s+प्रश्न\s+विचारला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+कडून\s+प्रश्न\s+आला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+ने\s+चर्चा\s+सुरू\s+केली'
    ]
    
    for pattern in additional_question_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in data["question_by"]:
                data["question_by"].append(match)
    
    # 6. Additional patterns for answer providers
    # Look for names followed by answer-related phrases
    additional_answer_patterns = [
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+यांनी\s+उत्तर\s+दिले',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+कडून\s+जबाब\s+आला',
        r'(?:श्रीमती|श्री|सर्वश्री)\.? ([^\n:,]+?)\s+ने\s+स्पष्टीकरण\s+दिले'
    ]
    
    for pattern in additional_answer_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if match not in data["answers_by"]:
                data["answers_by"].append(match)
    
    # Remove duplicates
    data["question_by"] = list(set(data["question_by"]))
    data["answers_by"] = list(set(data["answers_by"]))

    return data