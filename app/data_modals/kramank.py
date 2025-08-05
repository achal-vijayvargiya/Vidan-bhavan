from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from .Base import Base  # Base = declarative_base()

class Kramank(Base):
    __tablename__ = "kramanks"

    kramank_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    number = Column(String, nullable=False)
    date = Column(String, nullable=True)
    chairman = Column(String, nullable=True)
    document_name = Column(String, nullable=True)
    full_ocr_text = Column(Text, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="kramanks")
    debates = relationship("Debate", back_populates="kramank")
    