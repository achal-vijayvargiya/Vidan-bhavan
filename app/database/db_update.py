from sqlalchemy.orm import Session
from app.data_modals.session import Session as SessionModel
from app.data_modals.member import Member
from app.data_modals.resolution import Resolution
from app.data_modals.kramank import Kramank
from app.data_modals.debate import Debate

# Update Session
def update_session(db: Session, session_id, **kwargs):
    obj = db.query(SessionModel).filter_by(session_id=session_id).first()
    if obj:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    return obj

# Update Member
def update_member(db: Session, member_id, **kwargs):
    obj = db.query(Member).filter_by(member_id=member_id).first()
    if obj:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    return obj

# Update Resolution
def update_resolution(db: Session, resolution_id, **kwargs):
    obj = db.query(Resolution).filter_by(resolution_id=resolution_id).first()
    if obj:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    return obj

# Update Kramank
def update_kramank(db: Session, kramank_id, **kwargs):
    obj = db.query(Kramank).filter_by(kramank_id=kramank_id).first()
    if obj:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    return obj

# Update Debate
def update_debate(db: Session, debate_id, **kwargs):
    obj = db.query(Debate).filter_by(debate_id=debate_id).first()
    if obj:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        db.commit()
        db.refresh(obj)
    return obj 