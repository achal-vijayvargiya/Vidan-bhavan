from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from uuid import uuid4
from .Base import Base  # Base = declarative_base()

class Resolution(Base):
    __tablename__ = "resolutions"

    resolution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False)
    resolution_no = Column(String, nullable=False)
    resolution_no_en = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    image_name = Column(ARRAY(String), nullable=True)  # List of image names
    place = Column(String, nullable=True)

    # Optional: Relationship to session if you want backref
    session = relationship("Session", back_populates="resolutions")
