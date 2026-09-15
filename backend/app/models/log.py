from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ActionLog(Base):
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False)
    action = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    user = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    university = relationship("University", back_populates="logs")

    __table_args__ = (
        Index("idx_al_uni", "university_id"),
        Index("idx_al_action", "action"),
        Index("idx_al_time", "created_at"),
    )
