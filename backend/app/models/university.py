from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    vendor = Column(String(255), nullable=True)
    product = Column(String(255), nullable=True)
    contract_number = Column(String(50), nullable=True)
    license_signed = Column(Boolean, default=False)
    license_expiry_year = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, index=True)
    manager_name = Column(String(255), nullable=True, index=True)
    university_responsible = Column(String(255), nullable=True)
    comment = Column(Text, nullable=True)
    current_workflow_stage_id = Column(Integer, ForeignKey("workflow_stages.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow_stage = relationship("WorkflowStage", back_populates="universities")
    files = relationship("AttachedFile", back_populates="university")
    logs = relationship("ActionLog", back_populates="university")
    comments = relationship("Comment", back_populates="university")

    __table_args__ = (
        Index("idx_uni_name_status", "name", "status"),
        Index("idx_uni_manager", "manager_name"),
    )
