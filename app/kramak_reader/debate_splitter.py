import re
from typing import List, Dict, Any
from app.logging.logger import Logger
from rapidfuzz import fuzz

# Initialize logger
logger = Logger()

# Configuration
DEBUG_HEADING_MATCHING = False  # Set to True to enable detailed heading matching logs

def normalize_text(text: str) -> str:
    """Normalize text for better matching by removing extra spaces and punctuation"""
    # Remove extra whitespace and normalize
    normalized = re.sub(r'\s+', ' ', text.strip())
    # Remove common punctuation that might cause issues
    normalized = re.sub(r'[।॥]', '', normalized)
    # Remove common OCR artifacts
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

def find_heading_in_text(heading_text: str, page_text: str) -> int:
    """
    Find heading in page text with multiple fallback strategies
    Returns the start position or -1 if not found
    """
    # Strategy 1: Exact match
    start_pos = page_text.find(heading_text)
    if start_pos != -1:
        if DEBUG_HEADING_MATCHING:
            logger.debug(f"✅ Found exact match for heading: {heading_text[:30]}...")
        return start_pos
    
    # Strategy 2: Normalized match
    normalized_heading = normalize_text(heading_text)
    normalized_page = normalize_text(page_text)
    start_pos = normalized_page.find(normalized_heading)
    if start_pos != -1:
        # Find the corresponding position in original text
        # This is approximate but should work for most cases
        original_pos = page_text.find(heading_text[:10]) if len(heading_text) > 10 else -1
        if original_pos != -1:
            if DEBUG_HEADING_MATCHING:
                logger.debug(f"✅ Found normalized match for heading: {heading_text[:30]}...")
            return original_pos
    
    # Strategy 3: Fuzzy match for high similarity
    lines = page_text.split('\n')
    best_similarity = 0
    best_line = ""
    best_pos = -1
    
    for line in lines:
        if len(line.strip()) < 3:  # Skip very short lines
            continue
        similarity = fuzz.ratio(normalize_text(line), normalized_heading)
        if similarity > best_similarity:
            best_similarity = similarity
            best_line = line
            best_pos = page_text.find(line)
    
    if best_similarity > 85:  # High similarity threshold
        if DEBUG_HEADING_MATCHING:
            logger.debug(f"✅ Found fuzzy match (similarity {best_similarity}%) for heading: {heading_text[:30]}...")
        return best_pos
    elif best_similarity > 70:  # Medium similarity - log for debugging
        if DEBUG_HEADING_MATCHING:
            logger.debug(f"⚠️ High similarity ({best_similarity}%) but below threshold: '{heading_text[:30]}...' vs '{best_line[:30]}...'")
    
    # Strategy 4: Partial match (if heading is long enough)
    if len(heading_text) > 10:
        # Try to find a substring of the heading
        for i in range(len(heading_text) - 10, 5, -1):  # Try different lengths
            partial_heading = heading_text[:i]
            start_pos = page_text.find(partial_heading)
            if start_pos != -1:
                if DEBUG_HEADING_MATCHING:
                    logger.debug(f"✅ Found partial match for heading: {heading_text[:30]}... (partial: {partial_heading})")
                return start_pos
    
    # Strategy 5: Handle OCR artifacts and variations
    # Remove common OCR artifacts and try again
    cleaned_heading = re.sub(r'[^\w\s]', '', heading_text)  # Remove all punctuation
    if cleaned_heading != heading_text:
        start_pos = page_text.find(cleaned_heading)
        if start_pos != -1:
            if DEBUG_HEADING_MATCHING:
                logger.debug(f"✅ Found cleaned match for heading: {heading_text[:30]}...")
            return start_pos
    
    # Strategy 6: Try with different spacing patterns
    # Sometimes OCR adds extra spaces
    spaced_heading = ' '.join(heading_text.split())
    if spaced_heading != heading_text:
        start_pos = page_text.find(spaced_heading)
        if start_pos != -1:
            if DEBUG_HEADING_MATCHING:
                logger.debug(f"✅ Found spaced match for heading: {heading_text[:30]}...")
            return start_pos
    
    # Log detailed information for debugging
    if DEBUG_HEADING_MATCHING:
        logger.debug(f"❌ No match found for heading: '{heading_text[:50]}...'")
        logger.debug(f"Normalized heading: '{normalized_heading[:50]}...'")
        logger.debug(f"Best similarity found: {best_similarity}% with line: '{best_line[:50]}...'")
    
    return -1

def is_valid_heading(heading_text):
    """
    Check if the given heading_text is a valid heading using negative regex patterns.
    Returns True if valid, False if it matches any negative pattern.
    """
    if not heading_text or not isinstance(heading_text, str):
        return False

    # Negative patterns: if any matches, this is NOT a heading
    negative_patterns = [
        r"^बंदे\s+मातरम्",                # "Bande Mataram"
        r"^जयहिंद\s*!?\s*जयमहाराष्ट्र\s*!?", # "Jay Hind! Jay Maharashtra!"
        r"^\(\s*स्थगितीनंतर\s*\)",         # "( स्थगितीनंतर )"
        r"^\d{1,2}\s*मार्च\s*\d{4}",        # Date line
        r"^\d{1,2}\s*[A-Za-z]+\s*\d{4}",    # English date line
        r"^\s*$",                           # Empty or whitespace only
        r"^\d+$",                           # Only digits
        r"^\(.*\)$",                        # Any text starting with ( and ending with )
    ]

    for pat in negative_patterns:
        if re.search(pat, heading_text.strip()):
            return False
    return True


def process_ocr_headings(ocr_results: List[Dict]) -> List[Dict]:
    """
    Process OCR results and their headings.
    
    Args:
        ocr_results (List[Dict]): List of dictionaries containing OCR data per image
            Each dictionary has format:
            {
                "image": str,  # image filename
                "text": str,   # OCR text
                "headings": List[Dict]  # List of heading dictionaries with "text" key
            }
    """
    logger.info(f"Processing {len(ocr_results)} OCR result pages")
    try:
        debates = [] 
         
        # Process each page
        for ocr_item in ocr_results:
            try:
                image_name = ocr_item.get("image_name")
                text = ocr_item.get("text", "")
                headings = ocr_item.get("headings", [])
                
                logger.info(f"Page text length: {len(text)} characters")
                logger.info(f"Page headings found: {len(headings)}")
                
                if not text.strip():
                    logger.warning(f"⚠️ Empty text on page ")
                    continue
                    
                if not headings:
                    logger.warning(f"⚠️ No headings found on page")
                    # If this is a continuation page and we have previous debates
                    if debates:
                        # Append text to last debate
                        debates[-1]["text"] += "\n" + text
                        if image_name not in debates[-1]["image_name"]:
                            debates[-1]["image_name"].append(image_name)
                        logger.info(f"Added page text to previous debate: {debates[-1]['topic'][:50]}...")
                    continue
                
                # Process each heading in the current page
                for i, heading_text in enumerate(headings):
                    try:
                        logger.info(f"Processing heading {i+1}/{len(headings)}: {heading_text[:50]}...")
                        if not is_valid_heading(heading_text):
                            logger.warning(f"⚠️ Skipping invalid heading: {heading_text[:50]}...")
                            continue
                        # Use improved heading search
                        
                        start_pos = find_heading_in_text(heading_text, text)
                        if start_pos == -1:
                            logger.warning(f"⚠️ Couldn't find heading text in page content: {heading_text[:50]}...")
                            # Try to log some context for debugging
                            logger.debug(f"Page text preview: {text[:200]}...")
                            continue
                            
                        # Get end position - either start of next heading or end of text
                        if i < len(headings) - 1:
                            next_heading = headings[i + 1]
                            end_pos = text.find(next_heading)
                            if end_pos == -1:
                                end_pos = len(text)
                        else:
                            end_pos = len(text)
                            
                        # Extract text between current heading and next heading/end
                        debate_text = text[start_pos:end_pos].strip()
                        
                        # Process debate if we have enough content
                        if len(debate_text) > 1:
                            process_debate(debate_text, image_name, heading_text, debates)
                            logger.info(f"✅ Added debate with length {len(debate_text)}")
                        else:
                            logger.warning(f"⚠️ Skipped debate text (too short): {debate_text}")
                            
                    except Exception as heading_error:
                        logger.error(f"❌ Error processing heading: {str(heading_error)}")
                        continue
                        
            except Exception as page_error:
                logger.error(f"❌ Error processing page: {str(page_error)}")
                continue
                
        logger.info(f"✅ Extracted {len(debates)} debates from {len(ocr_results)} pages")
        logger.info("Debates found:")
        for i, debate in enumerate(debates, 1):
            logger.info(f"{i}. {debate['topic'][:50]}... ({len(debate['text'])} chars)")
            
        return debates
        
    except Exception as e:
        logger.error(f"❌ Critical error in process_ocr_headings: {str(e)}")
        return []

def process_debate(debate_text: str, image_name: str, heading_text: str, debates: List[Dict]) -> None:
    """Process a single debate and add it to the debates list"""
    try:
        # Clean up heading text
        heading_text = heading_text.strip()
        
        # Check if heading already exists in debates list
        heading_exists = len(debates) > 0 and debates[-1]["topic"].strip() == heading_text
        
        if heading_exists:
            # Append text to existing debate
            debates[-1]["text"] += "\n" + debate_text
            if image_name not in debates[-1]["image_name"]:
                debates[-1]["image_name"].append(image_name)
            logger.info(f"Updated existing debate: {heading_text[:50]}...")
        else:
            # Create new debate entry
            debates.append({
                "topic": heading_text,
                "text": debate_text,
                "image_name": [image_name]
            })
            logger.info(f"Created new debate: {heading_text[:50]}...")
    except Exception as e:
        logger.error(f"❌ Error in process_debate: {str(e)}")

