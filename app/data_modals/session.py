from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from .Base import Base  # Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    year = Column(Integer, nullable=False)
    house = Column(String, nullable=False)
    type = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    place = Column(String, nullable=True)
    status = Column(String, nullable=True)
    user = Column(String, nullable=True)
    last_update = Column(String, nullable=True)

    # Relationships to other tables (optional, for backrefs)
    members = relationship("Member", back_populates="session")
    kramanks = relationship("Kramank", back_populates="session")
    resolutions = relationship("Resolution", back_populates="session")  # Uncomment if you add back_populates in Resolution 