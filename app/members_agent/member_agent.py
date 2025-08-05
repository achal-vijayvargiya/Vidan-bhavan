"""
Member Agent for managing member data extraction from OCR results
"""

import logging
from typing import Dict, List, Optional
import json
from pathlib import Path
import sys

from app.logging.logger import Logger
from app.members_agent.member_parser.member_parser import MemberParser
from app.data_modals.member import Member
from app.database.db_insert import insert_member

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


logger = Logger()

class MemberAgent:
    """
    Agent for managing member data extraction from OCR results
    """
    
    def __init__(self):
        """Initialize MemberAgent"""
        self.member_parser = MemberParser()
        self.extracted_members = {
            "members": [],
            "total_count": 0
        }
        logger.info("✅ MemberAgent initialized")
        
    def process_ocr_result(self, ocr_result: Dict) -> Dict:
        """
        Process OCR result from kramank_reader agent to extract member information
        
        Args:
            ocr_result: Dictionary containing OCR results with keys:
                - text: Extracted text content
                - headings: List of detected headings
                - Image_path: Image path
                
        Returns:
            Dict containing:
                - members: List of extracted member information
                - total_count: Total number of members extracted
        """
        try:
            if not isinstance(ocr_result, list):
                logger.error("❌ Invalid OCR result format - expected list")
                return self.extracted_members
                
            # Initialize temporary storage for this batch of pages
            extracted_members = {
                "members": [],
                "total_count": 0
            }
           
            extracted_members=self.member_parser.process_text("\n".join([page_ocr['text'] for page_ocr in ocr_result]))
            # Extract text content from each page
                
                
            # Update the main extracted_members with results from all pages
            if extracted_members["members"]:
                self.extracted_members["members"].extend(extracted_members["members"])
                self.extracted_members["total_count"] = len(self.extracted_members["members"])
                logger.info(f"✅ Processed OCR result - Total members: {self.extracted_members['total_count']}")
            else:
                logger.warning("⚠️ No valid member data extracted from OCR result")
            
            return self.extracted_members
            
        except Exception as e:
            logger.error(f"❌ Error processing OCR result: {str(e)}")
            return self.extracted_members
            
    def save_to_db(self, members: List[Dict], session_id, house):
        """
        Save members to database
        """
        for member in members["members"]:
            member['session_id'] = session_id
            member['house'] = house
            member = Member(**member)
            insert_member(member)