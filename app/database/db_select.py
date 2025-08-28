from sqlalchemy.orm import Session
from app.data_modals.session import Session as SessionModel
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.data_modals.debate import Debate
from .db_conn_postgresql import get_db
from app.logging.logger import Logger
from typing import List, Optional

# Initialize logger
logger = Logger()

class DataFetcher:
    """
    A class to handle all database select operations with enhanced functionality
    """
    
    def __init__(self):
        self.db = None
    
    def _get_db_session(self):
        """Get database session"""
        if not self.db:
            self.db = next(get_db())
        return self.db
    
    def _close_db_session(self):
        """Close database session"""
        if self.db:
            self.db.close()
            self.db = None
    
    # ==================== SESSION OPERATIONS ====================
    
    def select_all_sessions(self) -> List[SessionModel]:
        """Select all sessions from database"""
        try:
            db = self._get_db_session()
            sessions = db.query(SessionModel).all()
            logger.info(f"✅ Retrieved {len(sessions)} sessions")
            return sessions
        except Exception as e:
            logger.error(f"❌ Error selecting all sessions: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_session_by_id(self, session_id: str) -> Optional[SessionModel]:
        """Select session by session ID"""
        try:
            db = self._get_db_session()
            session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if session:
                logger.info(f"✅ Retrieved session: {session_id}")
            else:
                logger.warning(f"⚠️ Session not found: {session_id}")
            return session
        except Exception as e:
            logger.error(f"❌ Error selecting session by ID {session_id}: {str(e)}")
            return None
        finally:
            self._close_db_session()
    
    def select_sessions_by_year(self, year: str) -> List[SessionModel]:
        """Select all sessions for a specific year"""
        try:
            db = self._get_db_session()
            sessions = db.query(SessionModel).filter(SessionModel.year == year).all()
            logger.info(f"✅ Retrieved {len(sessions)} sessions for year {year}")
            return sessions
        except Exception as e:
            logger.error(f"❌ Error selecting sessions by year {year}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    # ==================== MEMBER OPERATIONS ====================
    
    def select_all_members(self) -> List[Member]:
        """Select all members from database"""
        try:
            db = self._get_db_session()
            members = db.query(Member).all()
            logger.info(f"✅ Retrieved {len(members)} members")
            return members
        except Exception as e:
            logger.error(f"❌ Error selecting all members: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_member_by_id(self, member_id: str) -> Optional[Member]:
        """Select member by member ID"""
        try:
            db = self._get_db_session()
            member = db.query(Member).filter(Member.member_id == member_id).first()
            if member:
                logger.info(f"✅ Retrieved member: {member_id}")
            else:
                logger.warning(f"⚠️ Member not found: {member_id}")
            return member
        except Exception as e:
            logger.error(f"❌ Error selecting member by ID {member_id}: {str(e)}")
            return None
        finally:
            self._close_db_session()
    
    def select_members_by_session(self, session_id: str) -> List[Member]:
        """Select all members for a specific session"""
        try:
            db = self._get_db_session()
            members = db.query(Member).filter(Member.session_id == session_id).all()
            logger.info(f"✅ Retrieved {len(members)} members for session {session_id}")
            return members
        except Exception as e:
            logger.error(f"❌ Error selecting members by session {session_id}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    # ==================== RESOLUTION OPERATIONS ====================
    
    def select_all_resolutions(self) -> List[Resolution]:
        """Select all resolutions from database"""
        try:
            db = self._get_db_session()
            resolutions = db.query(Resolution).all()
            logger.info(f"✅ Retrieved {len(resolutions)} resolutions")
            return resolutions
        except Exception as e:
            logger.error(f"❌ Error selecting all resolutions: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_resolution_by_id(self, resolution_id: str) -> Optional[Resolution]:
        """Select resolution by resolution ID"""
        try:
            db = self._get_db_session()
            resolution = db.query(Resolution).filter(Resolution.resolution_id == resolution_id).first()
            if resolution:
                logger.info(f"✅ Retrieved resolution: {resolution_id}")
            else:
                logger.warning(f"⚠️ Resolution not found: {resolution_id}")
            return resolution
        except Exception as e:
            logger.error(f"❌ Error selecting resolution by ID {resolution_id}: {str(e)}")
            return None
        finally:
            self._close_db_session()
    
    def select_resolutions_by_session(self, session_id: str) -> List[Resolution]:
        """Select all resolutions for a specific session"""
        try:
            db = self._get_db_session()
            resolutions = db.query(Resolution).filter(Resolution.session_id == session_id).all()
            logger.info(f"✅ Retrieved {len(resolutions)} resolutions for session {session_id}")
            return resolutions
        except Exception as e:
            logger.error(f"❌ Error selecting resolutions by session {session_id}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    # ==================== KRAMANK OPERATIONS ====================
    
    def select_all_kramanks(self) -> List[Kramank]:
        """Select all kramanks from database"""
        try:
            db = self._get_db_session()
            kramanks = db.query(Kramank).all()
            logger.info(f"✅ Retrieved {len(kramanks)} kramanks")
            return kramanks
        except Exception as e:
            logger.error(f"❌ Error selecting all kramanks: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_kramank_by_id(self, kramank_id: str) -> Optional[Kramank]:
        """Select kramank by kramank ID"""
        try:
            db = self._get_db_session()
            kramank = db.query(Kramank).filter(Kramank.kramank_id == kramank_id).first()
            if kramank:
                logger.info(f"✅ Retrieved kramank: {kramank_id}")
            else:
                logger.warning(f"⚠️ Kramank not found: {kramank_id}")
            return kramank
        except Exception as e:
            logger.error(f"❌ Error selecting kramank by ID {kramank_id}: {str(e)}")
            return None
        finally:
            self._close_db_session()
    
    def select_kramanks_by_session_id(self, session_id: str) -> List[Kramank]:
        """Select all kramanks for a specific session ID"""
        try:
            db = self._get_db_session()
            kramanks = db.query(Kramank).filter(Kramank.session_id == session_id).all()
            logger.info(f"✅ Retrieved {len(kramanks)} kramanks for session {session_id}")
            return kramanks
        except Exception as e:
            logger.error(f"❌ Error selecting kramanks by session ID {session_id}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_kramanks_by_year(self, year: str) -> List[Kramank]:
        """Select all kramanks for a specific year"""
        try:
            db = self._get_db_session()
            # Join with sessions to filter by year
            kramanks = db.query(Kramank).join(SessionModel).filter(SessionModel.year == year).all()
            logger.info(f"✅ Retrieved {len(kramanks)} kramanks for year {year}")
            return kramanks
        except Exception as e:
            logger.error(f"❌ Error selecting kramanks by year {year}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    # ==================== DEBATE OPERATIONS ====================
    
    def select_all_debates(self) -> List[Debate]:
        """Select all active debates from database"""
        try:
            db = self._get_db_session()
            debates = db.query(Debate).filter(Debate.status == 'active').all()
            logger.info(f"✅ Retrieved {len(debates)} active debates")
            return debates
        except Exception as e:
            logger.error(f"❌ Error selecting all debates: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_debate_by_id(self, debate_id: str) -> Optional[Debate]:
        """Select debate by debate ID"""
        try:
            db = self._get_db_session()
            debate = db.query(Debate).filter(Debate.debate_id == debate_id).first()
            if debate:
                logger.info(f"✅ Retrieved debate: {debate_id}")
            else:
                logger.warning(f"⚠️ Debate not found: {debate_id}")
            return debate
        except Exception as e:
            logger.error(f"❌ Error selecting debate by ID {debate_id}: {str(e)}")
            return None
        finally:
            self._close_db_session()
    
    def select_debates_by_kramank_id(self, kramank_id: str) -> List[Debate]:
        """Select all active debates for a specific kramank ID"""
        try:
            db = self._get_db_session()
            debates = db.query(Debate).filter(
                Debate.kramank_id == kramank_id,
                Debate.status == 'active'
            ).all()
            logger.info(f"✅ Retrieved {len(debates)} active debates for kramank {kramank_id}")
            return debates
        except Exception as e:
            logger.error(f"❌ Error selecting debates by kramank ID {kramank_id}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_debates_by_session_id(self, session_id: str) -> List[Debate]:
        """Select all active debates for a specific session ID (through kramanks)"""
        try:
            db = self._get_db_session()
            # Join with kramanks to filter by session_id and only active debates
            debates = db.query(Debate).join(Kramank).filter(
                Kramank.session_id == session_id,
                Debate.status == 'active'
            ).all()
            logger.info(f"✅ Retrieved {len(debates)} active debates for session {session_id}")
            return debates
        except Exception as e:
            logger.error(f"❌ Error selecting debates by session ID {session_id}: {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_debates_by_topic(self, topic: str) -> List[Debate]:
        """Select active debates by topic (partial match)"""
        try:
            db = self._get_db_session()
            debates = db.query(Debate).filter(
                Debate.topic.ilike(f"%{topic}%"),
                Debate.status == 'active'
            ).all()
            logger.info(f"✅ Retrieved {len(debates)} active debates matching topic '{topic}'")
            return debates
        except Exception as e:
            logger.error(f"❌ Error selecting debates by topic '{topic}': {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    def select_debates_by_lob_type(self, lob_type: str) -> List[Debate]:
        """Select active debates by LOB type"""
        try:
            db = self._get_db_session()
            debates = db.query(Debate).filter(
                Debate.lob_type == lob_type,
                Debate.status == 'active'
            ).all()
            logger.info(f"✅ Retrieved {len(debates)} active debates with LOB type '{lob_type}'")
            return debates
        except Exception as e:
            logger.error(f"❌ Error selecting debates by LOB type '{lob_type}': {str(e)}")
            return []
        finally:
            self._close_db_session()
    
    # ==================== COMPOSITE QUERIES ====================
    
    def get_session_with_kramanks_and_debates(self, session_id: str) -> dict:
        """Get complete session data including kramanks and debates"""
        try:
            session = self.select_session_by_id(session_id)
            if not session:
                return {}
            
            kramanks = self.select_kramanks_by_session_id(session_id)
            debates = self.select_debates_by_session_id(session_id)
            
            result = {
                "session": session,
                "kramanks": kramanks,
                "debates": debates,
                "summary": {
                    "kramank_count": len(kramanks),
                    "debate_count": len(debates),
                    "total_debate_text_length": sum(len(d.text or "") for d in debates)
                }
            }
            
            logger.info(f"✅ Retrieved complete session data for {session_id}: {len(kramanks)} kramanks, {len(debates)} debates")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting complete session data for {session_id}: {str(e)}")
            return {}
    
    def get_kramank_with_debates(self, kramank_id: str) -> dict:
        """Get complete kramank data including debates"""
        try:
            kramank = self.select_kramank_by_id(kramank_id)
            if not kramank:
                return {}
            
            debates = self.select_debates_by_kramank_id(kramank_id)
            
            result = {
                "kramank": kramank,
                "debates": debates,
                "summary": {
                    "debate_count": len(debates),
                    "total_debate_text_length": sum(len(d.text or "") for d in debates),
                    "unique_topics": list(set(d.topic for d in debates if d.topic))
                }
            }
            
            logger.info(f"✅ Retrieved complete kramank data for {kramank_id}: {len(debates)} debates")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error getting complete kramank data for {kramank_id}: {str(e)}")
            return {}

# ==================== LEGACY FUNCTIONS (for backward compatibility) ====================

def select_all_sessions(db: Session):
    """Legacy function - use DataFetcher.select_all_sessions() instead"""
    fetcher = DataFetcher()
    return fetcher.select_all_sessions()

def select_all_members(db: Session):
    """Legacy function - use DataFetcher.select_all_members() instead"""
    fetcher = DataFetcher()
    return fetcher.select_all_members()

def select_all_resolutions(db: Session):
    """Legacy function - use DataFetcher.select_all_resolutions() instead"""
    fetcher = DataFetcher()
    return fetcher.select_all_resolutions()

def select_all_kramanks(db: Session):
    """Legacy function - use DataFetcher.select_all_kramanks() instead"""
    fetcher = DataFetcher()
    return fetcher.select_all_kramanks()

def select_all_debates(db: Session):
    """Legacy function - use DataFetcher.select_all_debates() instead"""
    fetcher = DataFetcher()
    return fetcher.select_all_debates() 