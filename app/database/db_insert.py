from sqlalchemy.orm import Session
from app.data_modals.session import Session as SessionModel
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.data_modals.debate import Debate
from .db_conn_postgresql import get_db
from app.logging.logger import Logger
import re

# Initialize logger
logger = Logger()

# Insert function for Session
def insert_session(session_obj: SessionModel) -> SessionModel:
    """Insert a Session object into the database or return existing session if found"""
    db = next(get_db())
    try:
        # Generate custom session ID using year, house, and session type
        year = session_obj.year or "UNKNOWN"
        house = session_obj.house or "UNKNOWN"
        session_type = session_obj.type or "REGULAR"
        
        # Create session ID in format: YEAR_HOUSE_TYPE
        custom_session_id = f"{year}_{house.upper()}_{session_type.upper()}"
        
        # Check if session already exists
        existing_session = db.query(SessionModel).filter(SessionModel.session_id == custom_session_id).first()
        if existing_session:
            return existing_session
        
        # If session doesn't exist, create new one
        session_obj.session_id = custom_session_id
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
        return session_obj
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Insert function for Member
def insert_member(member_obj: Member) -> Member:
    """Insert a Member object into the database"""
    db = next(get_db())
    try:
        db.add(member_obj)
        db.commit()
        db.refresh(member_obj)
        return member_obj
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Insert function for Resolution
def insert_resolution(resolution_obj: Resolution) -> Resolution:
    """Insert a Resolution object into the database"""
    db = next(get_db())
    try:
        db.add(resolution_obj)
        db.commit()
        db.refresh(resolution_obj)
        return resolution_obj
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Insert function for Kramank
def insert_kramank(kramank_obj: Kramank) -> Kramank:
    """Insert a Kramank object into the database"""
    db = next(get_db())
    try:
        # Generate custom kramank ID using session_id and number
        session_id = kramank_obj.session_id
        number = kramank_obj.number or "UNKNOWN"
        
        # Create kramank ID in format: SESSION_ID_KRAMANK_NUMBER
        custom_kramank_id = f"{session_id}_KRAMANK_{number}"
        
        # Check if kramank already exists
        existing_kramank = db.query(Kramank).filter(Kramank.kramank_id == custom_kramank_id).first()
        if existing_kramank:
            return existing_kramank
        
        # If kramank doesn't exist, create new one
        kramank_obj.kramank_id = custom_kramank_id
        db.add(kramank_obj)
        db.commit()
        db.refresh(kramank_obj)
        return kramank_obj
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

# Insert function for Debate
def insert_debate(debate_obj: Debate) -> Debate:
    """Insert a Debate object into the database"""
    db = next(get_db())
    try:
        # Validate debate object before insertion
        if not debate_obj.topic or not debate_obj.topic.strip():
            raise ValueError("Debate topic cannot be empty")
        
        if not debate_obj.kramank_id or not debate_obj.kramank_id.strip():
            raise ValueError("Kramank ID cannot be empty")
        
        # Clean and validate text fields
        if debate_obj.text:
            # Remove excessive whitespace
            debate_obj.text = re.sub(r'\s+', ' ', debate_obj.text.strip())
        
        if debate_obj.topic:
            debate_obj.topic = debate_obj.topic.strip()
        
        if debate_obj.document_name:
            debate_obj.document_name = debate_obj.document_name.strip()
        
        # Validate array fields
        if debate_obj.members and not isinstance(debate_obj.members, list):
            debate_obj.members = []
        
        if debate_obj.image_name and not isinstance(debate_obj.image_name, list):
            debate_obj.image_name = []
        
        # Clean array fields
        if debate_obj.members:
            debate_obj.members = [str(member).strip() for member in debate_obj.members if member and str(member).strip()]
        
        if debate_obj.image_name:
            debate_obj.image_name = [str(img).strip() for img in debate_obj.image_name if img and str(img).strip()]
        
        # Log the data being inserted for debugging
        logger.info(f"📝 Inserting debate: topic='{debate_obj.topic[:50]}...', kramank_id='{debate_obj.kramank_id}'")
        logger.info(f"📊 Debate data: text_length={len(debate_obj.text) if debate_obj.text else 0}, members={len(debate_obj.members)}")
        
        db.add(debate_obj)
        db.commit()
        db.refresh(debate_obj)
        
        logger.info(f"✅ Successfully inserted debate with ID: {debate_obj.debate_id}")
        return debate_obj
        
    except ValueError as ve:
        logger.error(f"❌ Validation error: {str(ve)}")
        db.rollback()
        raise ve
    except Exception as e:
        logger.error(f"❌ Database error inserting debate: {str(e)}")
        logger.error(f"Debate data: topic='{getattr(debate_obj, 'topic', 'None')}', kramank_id='{getattr(debate_obj, 'kramank_id', 'None')}'")
        db.rollback()
        raise e
    finally:
        db.close() 