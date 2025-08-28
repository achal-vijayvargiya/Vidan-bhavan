from sqlalchemy import Column, String, Text, ForeignKey, DateTime, ARRAY, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from uuid import uuid4
from .Base import Base  # Base = declarative_base()

class Debate(Base):
    __tablename__ = "debates"
    __table_args__ = (
        UniqueConstraint('kramank_id', 'sequence_number', name='uq_kramank_sequence'),
    )

    debate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_name = Column(String, nullable=False)
    kramank_id = Column(String, ForeignKey("kramanks.kramank_id"), nullable=False)
    date = Column(String, nullable=True)
    members = Column(ARRAY(String), nullable=True, default=[])  # PostgreSQL-only feature
    lob_type = Column(String, nullable=True)
    lob = Column(String, nullable=True)
    sub_lob = Column(String, nullable=True)
    question_no = Column(String, nullable=True)
    question_by = Column(String, nullable=True)
    answer_by = Column(String, nullable=True)
    ministry = Column(String, nullable=True)
    title = Column(Text, nullable=True)  # Add title field
    topic = Column(Text, nullable=False)
    text = Column(Text, nullable=True)
    image_name = Column(String, nullable=True)
    place = Column(String, nullable=True)
    status = Column(String, nullable=False, default='active')  # Values: 'active', 'deleted'
    sequence_number = Column(Integer, nullable=False)
    vol = Column(String, nullable=True)  # Volume/Khand number
    chairman = Column(String, nullable=True)  # Chairman name from kramank
    last_update = Column(String, nullable=True)  # Last update timestamp as string

    # Optional: Relationships
    kramank = relationship("Kramank", back_populates="debates")
