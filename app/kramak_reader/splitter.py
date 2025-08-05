import re
from typing import List, Dict, Tuple
from pathlib import Path
from app.logging.logger import Logger

# Initialize logger
logger = Logger()

debate_start_pattern = re.compile(
    r"""
    (?:विधानसभेची\s+बैठक.*?)?                       # Optional: विधानसभेची बैठक ...
    (?:(?:\b(?:सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार)\b)[,]?\s*)?  # Optional weekday
    (?:दिनांक\s*)?                                   # Optional 'दिनांक'
    \d{1,2}\s+                                        # Day (1–31)
    (?:जानेवारी|फेब्रुवारी|मार्च|एप्रिल|मे|जून|जुलै|ऑगस्ट|सप्टेंबर|ऑक्टोबर|नोव्हेंबर|डिसेंबर)\s+
    \d{2,4}                                           # Year
    (?:\s*रोजी)?                                      # Optional 'रोजी'
    (?:\s*(?:दुपारी|सकाळी|संध्याकाळी|सायंकाळी))?    # Optional time word
    """,
    re.VERBOSE
)

def is_debate_start(text: str) -> bool:
    return bool(debate_start_pattern.search(text))

def split_kramak_text(ocr_text: str) -> tuple[str, str, str]:
    logger.info("split_kramak_text called")
    try:
        text = ocr_text.strip()
        # Anchors
        member_start_pattern = r"महाराष्ट्र शासन\s+राज्यपाल"
        karyavali_start_pattern = r"कार्यावली\s+(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n"
        karyavali_end_pattern = r"(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n\s*विधानसभेची बैठक"
        logger.info("Searching for member, karyavali start, and karyavali end patterns")
        member_match = re.search(member_start_pattern, text)
        karyavali_start_match = re.search(karyavali_start_pattern, text)
        karyavali_end_match = re.search(karyavali_end_pattern, text)
        if not member_match:
            logger.error("❌ Members list start pattern not found.")
            return "", "", ocr_text
        if not karyavali_start_match:
            logger.error("❌ कार्यावली start pattern not found.")
            return "", "", ocr_text
        if not karyavali_end_match:
            logger.error("❌ Session start (end of कार्यावली) pattern not found.")
            return "", "", ocr_text
        member_start_index = member_match.start()
        karyavali_start_index = karyavali_start_match.start()
        karyavali_end_index = karyavali_end_match.start()
        if member_start_index > karyavali_start_index:
            logger.error("❌ कार्यावली appears before members list. Check OCR sequence.")
            raise ValueError("❌ कार्यावली appears before members list. Check OCR sequence.")
        members_list = text[member_start_index:karyavali_start_index].strip()
        karyavali_section = text[karyavali_start_index:karyavali_end_index].strip()
        remaining_text = text[karyavali_end_index:].strip()
        logger.info("split_kramak_text extraction complete")
        return members_list, karyavali_section, remaining_text
    except Exception as e:
        logger.error(f"Exception in split_kramak_text: {str(e)}")
        return "", "", ocr_text

def extract_adhyaksha(remaining_text: str) -> str:
    """
    Extracts:
    - अध्यक्ष line (session chairperson)
    - List of debates, each as a (heading, content) tuple
    """

    text = remaining_text.strip()

    # 1. Extract अध्यक्ष line (first line that starts with अध्यक्ष :)
    adhyaksha_pattern = r"अध्यक्ष\s*[:\-]\s*.*?अध्यक्षस्थानी होते"
    adhyaksha_match = re.search(adhyaksha_pattern, text)
    if adhyaksha_match:
        split_parts = re.split(r"अध्यक्ष\s*[:\-]\s*", adhyaksha_match.group(), maxsplit=1)
        if len(split_parts) > 1:
            return split_parts[1].strip()
        else:
            return adhyaksha_match.group().strip()
    if not adhyaksha_match:
        print("❌ अध्यक्ष line not found.")
        return ""

    adhyaksha_line = adhyaksha_match.group()
    return adhyaksha_line

def extract_date_from_marathi_text(text: str) -> str:
    """
    Extracts the first date from Marathi text.
    Looks for lines like: 'सोमवार, दिनांक २१ मार्च, २०२२' or similar.
    Returns only the first matched date string, or raises ValueError if not found.
    """
    import re

    # Pattern matches: (weekday), दिनांक (date) (month), (year)
    # Example: 'सोमवार, दिनांक २१ मार्च, २०२२'
    date_pattern = r"(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s*दिनांक\s*[०१२३४५६७८९0-9]{1,2}\s+[ए-ह्][\w]+,\s*[०१२३४५६७८९0-9]{4}"

    match = re.search(date_pattern, text)
    if not match:
        print("❌ Marathi date line not found.")
        return ""
    return match.group(0)

def extract_session_details(folder_path: str) -> Tuple[str, str, str, str]:
    """
    Extracts session details from folder path using regex patterns.
    
    Args:
        folder_path (str): Path to the session folder
        
    Returns:
        Tuple[str, str, str, str]: (year, house, session_type, kramak_name)
    """
    import re
    
    path_parts = Path(folder_path).parts
    
    # Extract year using regex pattern for 4 digits
    year_pattern = r'\d{4}'
    year = None
    for part in path_parts:
        year_match = re.search(year_pattern, part)
        if year_match:
            year = year_match.group()
            break
            
    # Extract house (MLA/MLC) using regex
    house_pattern = r'(MLA|MLC)'
    house = None
    for part in path_parts:
        house_match = re.search(house_pattern, part)
        if house_match:
            house = house_match.group()
            break
            
    # Extract session type from Session_X_Type format
    session_pattern = r'Session_\d+_(\w+)'
    session_type = None
    for part in path_parts:
        session_match = re.search(session_pattern, part)
        if session_match:
            session_type = session_match.group(1)
            break
            
    # Extract kramak name (should be last part of path)
    kramak_name = path_parts[-1]
    
    # Validate all required fields are found
    if not all([year, house, session_type, kramak_name]):
        print(f"Warning: Some session details could not be extracted:")
        print(f"Year: {year}")
        print(f"House: {house}")
        print(f"Session Type: {session_type}")
        print(f"Kramak Name: {kramak_name}")
        return None
    
    return year, house, session_type, kramak_name






