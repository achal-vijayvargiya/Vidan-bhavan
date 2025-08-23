from app.kramak_reader.kramak_ocr import kramank_ocr
from app.kramak_reader.splitter import split_kramak_text
from app.kramak_reader.debate_splitter import process_ocr_headings
from app.kramak_reader.splitter import extract_session_details
from pathlib import Path
from app.kramak_reader.kramak_ocr import kramank_ocr
from app.karyavali_parser.karyavali_parser import extract_karyavali_blocks
from app.kramak_reader.splitter import extract_date_from_marathi_text
from app.kramak_reader.splitter import extract_adhyaksha
import json
from app.logging.logger import Logger
from app.debate_agent.debate_agent import DebateAgent
from app.data_modals.session import Session
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.database.db_insert import insert_session, insert_member, insert_kramank, insert_resolution
from app.database.db_conn_postgresql import get_db
from app.index_parser.index_data_extracter import extract_index_data
from app.members_agent.member_agent import MemberAgent
import re

# Initialize logger
logger = Logger()

def agent_run(folder_path=None, kramak_name=None):
    logger.info(f"agent_run called with folder_path={folder_path}, kramak_name={kramak_name}")
    
    session_id = None
    kramak_id = None
    
    try:
        year, house, session_type, extracted_kramak_name = extract_session_details(folder_path)
        
        session_obj = Session(
            session_id=None,  # Will be set after DB insert if needed
            year=year,
            house=house,
            type=session_type,
            start_date=None,
            end_date=None,
            place=None
        )
        if not kramak_name:
            kramak_name = extracted_kramak_name
        logger.info(f"Session details extracted: year={year}, house={house}, type={session_type}, kramak_name={kramak_name}")

        # Save session details in the database
        session_obj = insert_session(session_obj=session_obj)
        session_id = session_obj.session_id
        logger.info(f"Session inserted/obtained: session_id={session_id}")

        # Prepare paths for saving/loading OCR results and text
        ocr_text_path = Path(folder_path) / "full_ocr_text.txt"
        ocr_results_path = Path(folder_path) / "ocr_results.json"

        # Check if both files exist
        if ocr_text_path.exists() and ocr_results_path.exists():
            logger.info("Loading OCR results and text from files")
            with open(ocr_text_path, "r", encoding="utf-8") as f:
                full_text = f.read()
            with open(ocr_results_path, "r", encoding="utf-8") as f:
                ocr_results = json.load(f)
        else:
            logger.info("Running kramank_ocr and saving results")
            ocr_results, full_text = kramank_ocr(folder_path, kramak_name)
            with open(ocr_text_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            with open(ocr_results_path, "w", encoding="utf-8") as f:
                json.dump(ocr_results, f, ensure_ascii=False, indent=2)
       
        adhyaksha_line = extract_adhyaksha(full_text)
        date_line = extract_date_from_marathi_text(full_text)
        index_data = extract_index_data(ocr_results.get('index', {}))
        #    if condition for kramak_name is 1 then extract karyavali data
        if str(kramak_name) == "1":
            karyavali_data = extract_karyavali_blocks(full_text)
        else:
            karyavali_data = []
        # Collect image names for karyawali pages (if any)
        karyawali_image_names = []
        try:
            karyawali_image_names = list({page.get('image_name') for page in ocr_results.get('karyawalis', []) if page.get('image_name')})
        except Exception:
            karyawali_image_names = []

        # Try to extract place from text (simple heuristic around 'विधानसभेची बैठक')
        place_match = re.search(r"विधानसभेची\s+बैठक[\s,:-]*([^\n]+)", full_text or "")
        place_value = place_match.group(1).strip() if place_match else None

        # Insert karyavali (resolution) data into the database
        inserted_resolutions = []
        for resolution in karyavali_data:
            try:
                # Prepare Resolution object (no kramank_id field in model)
                resolution_obj = Resolution(
                    session_id=session_id,
                    resolution_no=resolution.get("resolution_no") or resolution.get("number"),
                    resolution_no_en=resolution.get("resolution_no_en") or resolution.get("number_en") or resolution.get("number"),
                    text=resolution.get("text"),
                    image_name=resolution.get("image_name") or (karyawali_image_names if karyawali_image_names else None),
                    place=resolution.get("place") or place_value
                )
                inserted_resolution = insert_resolution(resolution_obj)
                inserted_resolutions.append(inserted_resolution)
                logger.info(f"Inserted resolution: {resolution_obj.resolution_no}")
            except Exception as e:
                logger.error(f"Failed to insert resolution {resolution.get('resolution_no') or resolution.get('number')}: {str(e)}")

        
        logger.info(f"Extracted adhyaksha: {adhyaksha_line}, date: {date_line}")
        
        
        
        # Extract and insert members from OCR (members pages)
        try:
            # if condition for kramak_name is 1 then extract members data
            if str(kramak_name) == "1":
                members_pages = ocr_results.get('members', [])
            else:
                members_pages = []
            if members_pages:
                logger.info(f"Extracting members from {len(members_pages)} pages")
                members_agent = MemberAgent()
                members_result = members_agent.process_ocr_result(members_pages)
                if members_result and members_result.get('members'):
                    members_agent.save_to_db(members_result, session_id=session_id, house=house)
                    logger.info(f"Inserted {len(members_result.get('members', []))} members for session {session_id}")
                else:
                    logger.info("No members extracted from OCR pages")
            else:
                logger.info("No members pages found in OCR results; skipping member extraction")
        except Exception as e:
            logger.error(f"Failed to extract/insert members: {str(e)}")
# Generate custom kramank ID
        custom_kramank_id = f"{session_id}_KRAMANK_{kramak_name}"
        
        # Create and insert kramank
        kramank_data = Kramank(
            kramank_id=custom_kramank_id,  # Set the ID explicitly
            session_id=session_id,
            number=kramak_name,
            date=date_line,
            chairman=adhyaksha_line,
            document_name=str(folder_path),
            full_ocr_text=full_text
        )

        # Insert kramank and get the inserted object back
        kramank_obj = insert_kramank(kramank_data)
        kramak_id = kramank_obj.kramank_id
        logger.info(f"Inserted kramank with id: {kramak_id}")

        # Process debates only if we have a valid kramak_id
        if kramak_id:
            debates_pages = ocr_results.get('debates', [])
            logger.info(f"Extracted {len(debates_pages)} debates pages from OCR results")
            debates = process_ocr_headings(debates_pages)
            
            # Initialize and run debate agent
            debates_agent = DebateAgent()
            debates_agent.process_debate(debates, session_id, kramak_id)
        else:
            logger.error("Failed to get kramak_id, skipping debate processing")
            
    except Exception as e:
        logger.error(f"Exception in agent_run: {str(e)}")
    