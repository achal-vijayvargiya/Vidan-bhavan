from .debate_type_identifier import identify_debate_type
from .field_extractor import extract_fields
from .db_storage import store_debate_data
from typing import List, Dict
from app.logging.logger import Logger
from app.data_modals.debate import Debate
from app.database.db_insert import insert_debate

logger = Logger()

class DebateAgent:
    def __init__(self):
        self.session_id = None
        self.kramak_id = None

    def process_debate(self, debates: List[dict], session_id: str, kramak_id: str) -> List[Dict]:
        """
        Process debates and store in database
        """
        self.session_id = session_id
        self.kramak_id = kramak_id
        
        logger.info(f"🎯 Processing {len(debates)} debates")
        
        processed_debates = []
        
        try:
            for i, debate in enumerate(debates, 1):
                try:
                    # Validate debate dictionary
                    if not isinstance(debate, dict):
                        logger.error(f"❌ Invalid debate format at index {i}: expected dictionary")
                        continue
                        
                    debate_topic = debate.get('topic', '')
                    if not debate_topic:
                        logger.warning(f"⚠️ No topic found for debate {i}, skipping...")
                        continue
                        
                    logger.info(f"📄 Processing debate {i}/{len(debates)}: {debate_topic[:50]}...")
                    
                    # Step 1: Identify debate type
                    logger.info(f"🔍 Classifying debate type...")
                    type_info = identify_debate_type(debate_topic)
                    
                    if type_info:
                        logger.info(f"✅ Debate classified: {type_info.get('lob', 'Unknown')} -> {type_info.get('lob_type', 'Unknown')}")
                    else:
                        logger.warning(f"⚠️  Failed to classify debate: {debate_topic[:50]}")
                        type_info = {
                            "lob": debate_topic,
                            "sub_lob": "none", 
                            "lob_type": "others"
                        }
                    
                    # Set required fields for debate
                    debate["document_name"] = debate.get("topic", "Unknown") + "_Document"
                    debate["kramank_id"] = kramak_id
                    debate["session_id"] = session_id
                    debate["lob"] = type_info.get("lob", "")
                    debate["sub_lob"] = type_info.get("sub_lob", "")
                    debate["lob_type"] = type_info.get("lob_type", "")
                    debate["members"] = debate.get("members", [])
                    debate["text"] = debate.get("text", "")
                    debate["image_name"] = debate.get("image_name", "")
                    
                    # Step 2: Extract fields
                    logger.info(f"📝 Extracting fields...")
                    debate_obj = extract_fields(debate, type_info)
                    
                    if debate_obj:
                        # Access Debate model attributes directly
                        logger.info(f"📊 Extracted fields: question_no={getattr(debate_obj, 'question_no', 'None')}, members={len(getattr(debate_obj, 'members', []))}")
                        logger.info(f"Debate text: {debate_obj.text}")
                        # Step 3: Store in DB
                        insert_debate(debate_obj)
                        
                        # Convert Debate object to dict for response
                        debate_dict = {
                            'debate_topic': debate_topic,
                            'classification': type_info,
                            'extracted_fields': {
                                'question_no': getattr(debate_obj, 'question_no', None),
                                'question_by': getattr(debate_obj, 'question_by', None),
                                'answer_by': getattr(debate_obj, 'answer_by', None),
                                'ministry': getattr(debate_obj, 'ministry', None),
                                'topic': getattr(debate_obj, 'topic', None),
                                'text': getattr(debate_obj, 'text', None),
                                'members': getattr(debate_obj, 'members', []),
                                'lob_type': getattr(debate_obj, 'lob_type', None),
                                'lob': getattr(debate_obj, 'lob', None),
                                'sub_lob': getattr(debate_obj, 'sub_lob', None)
                            },
                            'status': 'success'
                        }
                        processed_debates.append(debate_dict)
                        logger.info(f"✅ Debate {i} processed and stored successfully")
                    else:
                        logger.error(f"❌ Failed to extract fields for debate {i}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing debate {i}: {str(e)}")
                    processed_debates.append({
                        'debate_topic': debate.get('topic', 'Unknown'),
                        'status': 'error',
                        'error': str(e)
                    })
                    continue
            
            return processed_debates
            
        except Exception as e:
            logger.error(f"❌ Critical error in debate processing: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'processed_debates': processed_debates,
                'session_id': self.session_id,
                'kramak_id': self.kramak_id
            }