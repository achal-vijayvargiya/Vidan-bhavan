from typing import List, Optional, Dict, Any
from app.database.db_select import DataFetcher
from app.data_modals.session import Session as SessionModel
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.data_modals.debate import Debate
from app.logging.logger import Logger
import json
from datetime import datetime

# Initialize logger
logger = Logger()

class ApiService:
    """
    Service layer class that provides API endpoints with business logic
    using DataFetcher for database operations
    """
    
    def __init__(self):
        self.data_fetcher = DataFetcher()
    
    # ==================== SESSION SERVICES ====================
    
    def get_all_sessions(self) -> Dict[str, Any]:
        """Get all sessions with summary statistics"""
        try:
            sessions = self.data_fetcher.select_all_sessions()
            
            # Calculate summary statistics
            total_sessions = len(sessions)
            years = list(set(session.year for session in sessions if session.year))
            house_types = list(set(session.house for session in sessions if session.house))
            
            result = {
                "success": True,
                "data": {
                    "sessions": [self._serialize_session(session) for session in sessions],
                    "summary": {
                        "total_sessions": total_sessions,
                        "years": sorted(years),
                        "house_types": sorted(house_types)
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {total_sessions} sessions via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_sessions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"sessions": [], "summary": {"total_sessions": 0, "years": [], "house_types": []}}
            }
    
    def get_session_by_id(self, session_id: str) -> Dict[str, Any]:
        """Get session by ID with complete details"""
        try:
            session = self.data_fetcher.select_session_by_id(session_id)
            
            if not session:
                return {
                    "success": False,
                    "error": f"Session not found: {session_id}",
                    "data": None
                }
            
            result = {
                "success": True,
                "data": self._serialize_session(session)
            }
            
            logger.info(f"✅ Retrieved session {session_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_session_by_id: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def get_sessions_by_year(self, year: str) -> Dict[str, Any]:
        """Get all sessions for a specific year"""
        try:
            sessions = self.data_fetcher.select_sessions_by_year(year)
            
            result = {
                "success": True,
                "data": {
                    "year": year,
                    "sessions": [self._serialize_session(session) for session in sessions],
                    "count": len(sessions)
                }
            }
            
            logger.info(f"✅ Retrieved {len(sessions)} sessions for year {year} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_sessions_by_year: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"year": year, "sessions": [], "count": 0}
            }
    
    def get_complete_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get complete session data including kramanks and debates"""
        try:
            session_data = self.data_fetcher.get_session_with_kramanks_and_debates(session_id)
            
            if not session_data:
                return {
                    "success": False,
                    "error": f"Session not found: {session_id}",
                    "data": None
                }
            
            # Serialize the data
            result = {
                "success": True,
                "data": {
                    "session": self._serialize_session(session_data["session"]),
                    "kramanks": [self._serialize_kramank(k) for k in session_data["kramanks"]],
                    "debates": [self._serialize_debate(d) for d in session_data["debates"]],
                    "summary": session_data["summary"]
                }
            }
            
            logger.info(f"✅ Retrieved complete session data for {session_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_complete_session_data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    # ==================== MEMBER SERVICES ====================
    
    def get_all_members(self) -> Dict[str, Any]:
        """Get all members with summary statistics"""
        try:
            members = self.data_fetcher.select_all_members()
            
            result = {
                "success": True,
                "data": {
                    "members": [self._serialize_member(member) for member in members],
                    "summary": {
                        "total_members": len(members),
                        "unique_sessions": list(set(member.session_id for member in members if member.session_id))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(members)} members via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_members: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"members": [], "summary": {"total_members": 0, "unique_sessions": []}}
            }
    
    def get_members_by_session(self, session_id: str) -> Dict[str, Any]:
        """Get all members for a specific session"""
        try:
            members = self.data_fetcher.select_members_by_session(session_id)
            
            result = {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "members": [self._serialize_member(member) for member in members],
                    "count": len(members)
                }
            }
            
            logger.info(f"✅ Retrieved {len(members)} members for session {session_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_members_by_session: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"session_id": session_id, "members": [], "count": 0}
            }
    
    # ==================== KRAMANK SERVICES ====================
    
    def get_all_kramanks(self) -> Dict[str, Any]:
        """Get all kramanks with summary statistics"""
        try:
            kramanks = self.data_fetcher.select_all_kramanks()
            
            result = {
                "success": True,
                "data": {
                    "kramanks": [self._serialize_kramank(kramank) for kramank in kramanks],
                    "summary": {
                        "total_kramanks": len(kramanks),
                        "unique_sessions": list(set(kramank.session_id for kramank in kramanks if kramank.session_id))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(kramanks)} kramanks via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_kramanks: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"kramanks": [], "summary": {"total_kramanks": 0, "unique_sessions": []}}
            }
    
    def get_kramanks_by_session_id(self, session_id: str) -> Dict[str, Any]:
        """Get all kramanks for a specific session ID"""
        try:
            kramanks = self.data_fetcher.select_kramanks_by_session_id(session_id)
            
            result = {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "kramanks": [self._serialize_kramank(kramank) for kramank in kramanks],
                    "count": len(kramanks)
                }
            }
            
            logger.info(f"✅ Retrieved {len(kramanks)} kramanks for session {session_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_kramanks_by_session_id: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"session_id": session_id, "kramanks": [], "count": 0}
            }
    
    def get_kramank_with_debates(self, kramank_id: str) -> Dict[str, Any]:
        """Get complete kramank data including debates"""
        try:
            kramank_data = self.data_fetcher.get_kramank_with_debates(kramank_id)
            
            if not kramank_data:
                return {
                    "success": False,
                    "error": f"Kramank not found: {kramank_id}",
                    "data": None
                }
            
            result = {
                "success": True,
                "data": {
                    "kramank": self._serialize_kramank(kramank_data["kramank"]),
                    "debates": [self._serialize_debate(d) for d in kramank_data["debates"]],
                    "summary": kramank_data["summary"]
                }
            }
            
            logger.info(f"✅ Retrieved complete kramank data for {kramank_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_kramank_with_debates: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    # ==================== DEBATE SERVICES ====================
    
    def get_all_debates(self) -> Dict[str, Any]:
        """Get all active debates with summary statistics"""
        try:
            debates = self.data_fetcher.select_all_debates()
            
            result = {
                "success": True,
                "data": {
                    "debates": [self._serialize_debate(debate) for debate in debates],
                    "summary": {
                        "total_debates": len(debates),
                        "total_text_length": sum(len(debate.text or "") for debate in debates),
                        "unique_topics": list(set(debate.topic for debate in debates if debate.topic)),
                        "lob_types": list(set(debate.lob_type for debate in debates if debate.lob_type))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(debates)} active debates via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_debates: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"debates": [], "summary": {"total_debates": 0, "total_text_length": 0, "unique_topics": [], "lob_types": []}}
            }
    
    def get_debates_by_kramank_id(self, kramank_id: str) -> Dict[str, Any]:
        """Get all debates for a specific kramank ID"""
        try:
            debates = self.data_fetcher.select_debates_by_kramank_id(kramank_id)
            
            result = {
                "success": True,
                "data": {
                    "kramank_id": kramank_id,
                    "debates": [self._serialize_debate(debate) for debate in debates],
                    "count": len(debates),
                    "summary": {
                        "total_text_length": sum(len(debate.text or "") for debate in debates),
                        "unique_topics": list(set(debate.topic for debate in debates if debate.topic))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(debates)} debates for kramank {kramank_id} via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_debates_by_kramank_id: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"kramank_id": kramank_id, "debates": [], "count": 0, "summary": {"total_text_length": 0, "unique_topics": []}}
            }
    
    def get_debates_by_topic(self, topic: str) -> Dict[str, Any]:
        """Get debates by topic (partial match)"""
        try:
            debates = self.data_fetcher.select_debates_by_topic(topic)
            
            result = {
                "success": True,
                "data": {
                    "topic": topic,
                    "debates": [self._serialize_debate(debate) for debate in debates],
                    "count": len(debates),
                    "summary": {
                        "total_text_length": sum(len(debate.text or "") for debate in debates),
                        "unique_kramanks": list(set(debate.kramank_id for debate in debates if debate.kramank_id))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(debates)} debates matching topic '{topic}' via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_debates_by_topic: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"topic": topic, "debates": [], "count": 0, "summary": {"total_text_length": 0, "unique_kramanks": []}}
            }
    
    def get_debates_by_lob_type(self, lob_type: str) -> Dict[str, Any]:
        """Get debates by LOB type"""
        try:
            debates = self.data_fetcher.select_debates_by_lob_type(lob_type)
            
            result = {
                "success": True,
                "data": {
                    "lob_type": lob_type,
                    "debates": [self._serialize_debate(debate) for debate in debates],
                    "count": len(debates),
                    "summary": {
                        "total_text_length": sum(len(debate.text or "") for debate in debates),
                        "unique_topics": list(set(debate.topic for debate in debates if debate.topic))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(debates)} debates with LOB type '{lob_type}' via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_debates_by_lob_type: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"lob_type": lob_type, "debates": [], "count": 0, "summary": {"total_text_length": 0, "unique_topics": []}}
            }
    
    # ==================== RESOLUTION SERVICES ====================
    
    def get_all_resolutions(self) -> Dict[str, Any]:
        """Get all resolutions with summary statistics"""
        try:
            resolutions = self.data_fetcher.select_all_resolutions()
            
            result = {
                "success": True,
                "data": {
                    "resolutions": [self._serialize_resolution(resolution) for resolution in resolutions],
                    "summary": {
                        "total_resolutions": len(resolutions),
                        "unique_sessions": list(set(resolution.session_id for resolution in resolutions if resolution.session_id))
                    }
                }
            }
            
            logger.info(f"✅ Retrieved {len(resolutions)} resolutions via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_all_resolutions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"resolutions": [], "summary": {"total_resolutions": 0, "unique_sessions": []}}
            }
    
    def get_resolutions_by_session(self, session_id: str) -> Dict[str, Any]:
        """Get all resolutions for a specific session"""
        try:
            resolutions = self.data_fetcher.select_resolutions_by_session(session_id)
            logger.info(f"✅ Retrieved {len(resolutions)} resolutions for session {session_id} via API")
            
            # Debug: Check the first resolution object
            if resolutions:
                first_resolution = resolutions[0]
                logger.info(f"Debug: First resolution object type: {type(first_resolution)}")
                logger.info(f"Debug: First resolution attributes: {dir(first_resolution)}")
                logger.info(f"Debug: First resolution resolution_no_en: {getattr(first_resolution, 'resolution_no_en', 'NOT_FOUND')}")
            
            serialized_resolutions = []
            for i, resolution in enumerate(resolutions):
                try:
                    serialized = self._serialize_resolution(resolution)
                    serialized_resolutions.append(serialized)
                except Exception as serialize_error:
                    logger.error(f"❌ Error serializing resolution {i}: {str(serialize_error)}")
                    logger.error(f"❌ Resolution object: {resolution}")
                    logger.error(f"❌ Resolution attributes: {dir(resolution)}")
                    # Continue with other resolutions
                    continue
            
            result = {
                "success": True,
                "data": {
                    "session_id": session_id,
                    "resolutions": serialized_resolutions,
                    "count": len(serialized_resolutions)
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_resolutions_by_session: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"session_id": session_id, "resolutions": [], "count": 0}
            }
    
    # ==================== SEARCH AND ANALYTICS SERVICES ====================
    
    def search_debates(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search debates by topic or text content"""
        try:
            # Search by topic first
            topic_debates = self.data_fetcher.select_debates_by_topic(query)
            
            # Limit results
            if len(topic_debates) > limit:
                topic_debates = topic_debates[:limit]
            
            result = {
                "success": True,
                "data": {
                    "query": query,
                    "debates": [self._serialize_debate(debate) for debate in topic_debates],
                    "count": len(topic_debates),
                    "search_type": "topic_match"
                }
            }
            
            logger.info(f"✅ Search completed for '{query}' via API: {len(topic_debates)} results")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in search_debates: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"query": query, "debates": [], "count": 0, "search_type": "topic_match"}
            }
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            # Get counts from all tables
            sessions = self.data_fetcher.select_all_sessions()
            members = self.data_fetcher.select_all_members()
            kramanks = self.data_fetcher.select_all_kramanks()
            debates = self.data_fetcher.select_all_debates()
            resolutions = self.data_fetcher.select_all_resolutions()
            
            # Calculate statistics
            total_text_length = sum(len(debate.text or "") for debate in debates)
            unique_topics = len(set(debate.topic for debate in debates if debate.topic))
            unique_sessions = len(set(session.session_id for session in sessions if session.session_id))
            
            result = {
                "success": True,
                "data": {
                    "statistics": {
                        "sessions": len(sessions),
                        "members": len(members),
                        "kramanks": len(kramanks),
                        "debates": len(debates),
                        "resolutions": len(resolutions),
                        "total_text_length": total_text_length,
                        "unique_topics": unique_topics,
                        "unique_sessions": unique_sessions
                    },
                    "last_updated": datetime.now().isoformat()
                }
            }
            
            logger.info(f"✅ Retrieved database statistics via API")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in get_database_statistics: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {"statistics": {}, "last_updated": datetime.now().isoformat()}
            }
    
    # ==================== SERIALIZATION HELPERS ====================
    
    def _serialize_session(self, session: SessionModel) -> Dict[str, Any]:
        """Serialize session object to dictionary"""
        return {
            "session_id": session.session_id,
            "year": session.year,
            "house": session.house,
            "type": session.type,
            "start_date": session.start_date,
            "end_date": session.end_date,
            "place": session.place
        }
    
    def _serialize_member(self, member: Member) -> Dict[str, Any]:
        """Serialize member object to dictionary"""
        return {
            "id": str(member.member_id),  # Changed from member_id to id for UI compatibility
            "session_id": member.session_id,
            "name": member.name,
            "house": member.house,
            "party": member.party,
            "ministry": member.ministry,
            "role": member.role,
            "gender": member.gender,
            "contact": member.contact,
            "address": member.address,
            "image_url": member.image_url,
            "aka": member.aka,
            # Additional fields expected by UI
            "status": "active",  # Default status
            "user": "system",  # Default user
            "last_update": "2024-01-01",  # Default date
            # Aliases for UI compatibility
            "position": member.role,  # Alias for role
            "department": member.ministry,  # Alias for ministry
            "number": str(member.member_id),  # Fixed: Convert UUID to string
            "date": "2024-01-01",  # Default date
            "chairman": member.name  # Alias for name
        }
    
    def _serialize_kramank(self, kramank: Kramank) -> Dict[str, Any]:
        """Serialize kramank object to dictionary"""
        return {
            "kramank_id": str(kramank.kramank_id) if hasattr(kramank.kramank_id, '__str__') else kramank.kramank_id,
            "session_id": kramank.session_id,
            "number": kramank.number,
            "date": kramank.date,
            "chairman": kramank.chairman,
            "document_name": kramank.document_name,
            "full_ocr_text_length": len(kramank.full_ocr_text) if kramank.full_ocr_text else 0
        }
    
    def _serialize_debate(self, debate: Debate) -> Dict[str, Any]:
        """Serialize debate object to dictionary"""
        return {
            "id": str(debate.debate_id),  # Changed from debate_id to id for UI compatibility
            "document_name": debate.document_name,
            "kramank_id": str(debate.kramank_id) if hasattr(debate.kramank_id, '__str__') else debate.kramank_id,
            "sequence_number": debate.sequence_number,  # Add sequence number
            "date": debate.date,
            "members": debate.members,
            "lob_type": debate.lob_type,
            "lob": debate.lob,
            "sub_lob": debate.sub_lob,
            "question_no": debate.question_no,
            "question_by": debate.question_by,
            "answer_by": debate.answer_by,
            "ministry": debate.ministry,
            "title": debate.title,  # Add title field
            "topic": debate.topic,
            "text": debate.text,  # Added full text for UI
            "text_length": len(debate.text) if debate.text else 0,
            "text_preview": debate.text[:200] + "..." if debate.text and len(debate.text) > 200 else debate.text,
            "image_name": debate.image_name,
            "place": debate.place,
            # Additional fields expected by UI
            "status": debate.status,  # Use actual status from database
            "user": "system",  # Default user
            "last_update": debate.date,  # Use date as last update
            "question_number": debate.question_no,  # Alias for question_no
            "topics": debate.topic,  # Alias for topic
        }
    
    def _serialize_resolution(self, resolution: Resolution) -> Dict[str, Any]:
        """Serialize resolution object to dictionary"""
        try:
            return {
                "resolution_id": str(resolution.resolution_id) if hasattr(resolution.resolution_id, '__str__') else resolution.resolution_id,
                "session_id": getattr(resolution, 'session_id', ''),
                "resolution_no": getattr(resolution, 'resolution_no', ''),
                "resolution_no_en": getattr(resolution, 'resolution_no_en', ''),
                "title": getattr(resolution, 'resolution_no_en', ''),  # Use resolution_no_en as title
                "content": getattr(resolution, 'text', ''),  # Use text as content
                "text": getattr(resolution, 'text', ''),
                "image_name": getattr(resolution, 'image_name', []),
                "place": getattr(resolution, 'place', ''),
                # Additional fields for UI compatibility
                "date": getattr(resolution, 'place', ''),  # Use place as date (temporary)
                "status": "active"  # Default status
            }
        except Exception as e:
            logger.error(f"❌ Error in _serialize_resolution: {str(e)}")
            logger.error(f"❌ Resolution object: {resolution}")
            logger.error(f"❌ Resolution attributes: {dir(resolution)}")
            # Return a safe fallback
            return {
                "resolution_id": "error",
                "session_id": "",
                "resolution_no": "",
                "resolution_no_en": "",
                "title": "Error loading resolution",
                "content": "",
                "text": "",
                "image_name": [],
                "place": "",
                "date": "",
                "status": "error"
            }
