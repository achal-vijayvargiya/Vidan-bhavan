from typing import Dict
from pathlib import Path
from google.cloud import vision
from app.ocr.vision_ocr import setup_vision_client
from app.kramak_reader.splitter import is_debate_start
import re
from rapidfuzz import fuzz
from pathlib import Path
from typing import Tuple, List, Optional
from app.logging.logger import Logger
import json
# Initialize logger
logger = Logger()

def detect_page_type(text: str, current_section: str) -> str:
    """
    Detect the section type for the given text and current section.
    Returns the new section name ("index", "members", "karyawalis", "debates").
    """
    member_start_pattern = r"महाराष्ट्र शासन\s+राज्यपाल"
    karyavali_start_pattern = r"कार्यावली\s+(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n"
    karyavali_end_pattern = r"(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n\s*विधानसभेची बैठक"

    member_match = re.search(member_start_pattern, text)
    karyavali_start_match = re.search(karyavali_start_pattern, text)
    karyavali_end_match = re.search(karyavali_end_pattern, text)

    if current_section == "index" and member_match:
        return "members"
    if current_section == "members" and karyavali_start_match:
        return "karyawalis"
    if current_section == "karyawalis" and karyavali_end_match:
        return "debates"
    return current_section

def kramank_ocr(folder_path: str, kramak_name: str) -> Dict:
    logger.info(f"kramank_ocr called with folder_path={folder_path}, kramak_name={kramak_name}")
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Invalid folder path: {folder_path}")
    
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp'}
    image_files = sorted(f for f in folder.glob('*') if f.suffix.lower() in image_extensions)
    
    if not image_files:
        raise ValueError(f"No image files found in {folder_path}")
    
    print(f"Found {len(image_files)} image files to process")
    ocr_results = {}
    final_ocr_text = ""

    current_section = "index"

    for image_file in image_files:
        try:
            result  = extract_text_from_image(str(image_file))
            text = result["text"].strip()
            page_ocr = {
                "text": result["text"],
                "headings": result["headings"],
                "image_name": image_file.name
            }

            # Use detect_page_type to determine section
            new_section = detect_page_type(text, current_section)
            current_section = new_section
            # INSERT_YOUR_CODE
            # If filename ends with a char (not a number), put page_ocr in ocr_results["index"]
            base_name = image_file.stem
            if base_name and not base_name[-1].isdigit():
                if "index" not in ocr_results:
                    ocr_results["index"] = []
                ocr_results["index"].append(page_ocr)
                # Continue to next image, skip normal section logic
                continue
            # Populate ocr_results based on current section
            if current_section == "index":
                if "index" not in ocr_results:
                    ocr_results["index"] = []
                ocr_results["index"].append(page_ocr)
            elif current_section == "members":
                if "members" not in ocr_results:
                    ocr_results["members"] = []
                ocr_results["members"].append(page_ocr)
            elif current_section == "karyawalis":
                if "karyawalis" not in ocr_results:
                    ocr_results["karyawalis"] = []
                ocr_results["karyawalis"].append(page_ocr)
            elif current_section == "debates":
                if "debates" not in ocr_results:
                    ocr_results["debates"] = []
                ocr_results["debates"].append(page_ocr)

            final_ocr_text += result["text"]
            print(f"✅ OCR: {image_file.name}")
        except Exception as e:
            print(f"❌ Error processing {image_file.name}: {str(e)}")

    if not ocr_results:
        raise ValueError("No text could be extracted from any images.")

    logger.info("OCR processing complete")
    return ocr_results, final_ocr_text

def detect_page_type_old(ocr_results: dict, page_ocr :dict) :
    text = page_ocr["text"].strip()
    # Heuristics for detection
    # 1. Members list: Look for keywords like 'महाराष्ट्र शासन', 'राज्यपाल', 'सदस्यांची यादी'
    member_start_pattern = r"महाराष्ट्र शासन\s+राज्यपाल"
    member_match = re.search(member_start_pattern, text)
    karyavali_start_pattern = r"कार्यावली\s+(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n"   
    karyavali_start_match = re.search(karyavali_start_pattern, text)
    karyavali_end_pattern = r"(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n\s*विधानसभेची बैठक"
    karyavali_end_match = re.search(karyavali_end_pattern, text)

    # if not member_match and "members" not in ocr_results and len(ocr_results) <= 1:
    # # If "index" key does not exist in ocr_results, add it as an empty list
    #     if "index" not in ocr_results:
    #         ocr_results["index"] = []
    #     # Append page_ocr to the "index" list
    #     ocr_results["index"].append(page_ocr)
    # elif member_match and len(ocr_results) < 3 and len(ocr_results) >= 2:
    #     if "members" not in ocr_results:
    #         ocr_results["members"] = []
    #     ocr_results["members"].append(page_ocr)

    # if karyavali_start_match and len(ocr_results) < 4 and len(ocr_results) >= 2:
    #     if "karyawalis" not in ocr_results:
    #         ocr_results["karyawalis"] = []
    #     ocr_results["karyawalis"].append(page_ocr)

    if karyavali_end_match:
        return True


def detect_page_type_index_debates(ocr_results: dict, page_ocr: dict):
    text = page_ocr["text"].strip()
    # Index detection (same as before)
    member_start_pattern = r"महाराष्ट्र शासन\s+राज्यपाल"
    member_match = re.search(member_start_pattern, text)
    karyavali_end_pattern = r"(सोमवार|मंगळवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार),\s+दिनांक.*?\n\s*विधानसभेची बैठक"
    karyavali_end_match = re.search(karyavali_end_pattern, text)
    if not member_match and ("index" not in ocr_results or len(ocr_results) < 2):
        if "index" not in ocr_results:
            ocr_results["index"] = []
        ocr_results["index"].append(page_ocr)
    if karyavali_end_match:
        if "debates" not in ocr_results:
            ocr_results["debates"] = []
        ocr_results["debates"].append(page_ocr)

def estimate_font_height(bbox):
    y_top = min(v.y for v in bbox.vertices)
    y_bottom = max(v.y for v in bbox.vertices)
    return abs(y_bottom - y_top)

def is_center_aligned(bbox, page_width, margin=0.15):
    x_left = min(v.x for v in bbox.vertices)
    x_right = max(v.x for v in bbox.vertices)
    center = (x_left + x_right) / 2
    return abs(center - (page_width / 2)) < page_width * margin

def check_lob_match(line_text: str) -> Dict:
        """
        Check if the given line_text matches any lob or sub_lob from lob_master.json
        Returns the matching JSON item if found, otherwise None
        """
        try:
            # Load lob_master.json
            lob_master_path = Path(__file__).parent.parent / "master_data" / "lob_master.json"
            with open(lob_master_path, 'r', encoding='utf-8') as f:
                lob_data = json.load(f)
            
            # Clean the line_text for comparison
            cleaned_text = line_text.strip()
            
            # Check for exact matches in lob and sub_lob
            for item in lob_data:
                # Check main lob
                if item.get('lob') == cleaned_text:
                    return item
                
                # Check sub_lob items
                sub_lobs = item.get('sub_lob', [])
                for sub_lob in sub_lobs:
                    if sub_lob == cleaned_text:
                        return {
                            "lob": item.get('lob'),
                            "sub_lob": [sub_lob],
                            "lob_type": item.get('lob_type')
                        }
                       
            
            return {"lob": cleaned_text, "sub_lob": [], "lob_type": "others"}
            
        except Exception as e:
            print(f"Error checking lob match: {str(e)}")
            return None




def extract_text_from_image(image_path: str) -> Dict:
    client = setup_vision_client()
    result = {
        "text": "",
        "headings": []
    }

    with open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(f"OCR Error: {response.error.message}")

    if not response.full_text_annotation:
        return result

    # Full plain text
    result["text"] = response.full_text_annotation.text
    
   
    page = response.full_text_annotation.pages[0]
    page_width = page.width

    for block in page.blocks:
        for para in block.paragraphs:
            line_text = ""
            for word in para.words:
                line_text += "".join([s.text for s in word.symbols]) + " "

            font_height = estimate_font_height(para.bounding_box)
            if (
                is_center_aligned(para.bounding_box, page_width)
                and font_height >= 25
                and 5 < len(line_text.strip()) < 50
            ):
                result["headings"].append(line_text)

    return result

    