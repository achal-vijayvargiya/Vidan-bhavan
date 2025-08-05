from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from .Base import Base  # Base = declarative_base()

class Member(Base):
    __tablename__ = "members"

    member_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    house = Column(String, nullable=True)
    party = Column(String, nullable=True)
    ministry = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    address = Column(String, nullable=True)
    role = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    aka = Column(String, nullable=True)

    # Optional: Relationship to session if you want backref
    session = relationship("Session", back_populates="members")
    