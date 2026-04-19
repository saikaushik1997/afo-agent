from typing import Optional
import uuid

from pydantic import BaseModel
from sqlalchemy import Column, Float, String, Text
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from sqlalchemy import Column, DateTime


class Base(DeclarativeBase):
    pass

# SQL Model
class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())) # primary key - UUID
    message_id = Column(String, nullable=True) # email's ID from the mail server
    filename = Column(String, nullable=False) # uploaded file in the email
    status = Column(String, default="received")  # received | processing | completed | failed | pending_review
    doc_type = Column(String, nullable=True)      # invoice | capital_call
    fund_name = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# FastAPI Model
class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    doc_type: Optional[str]
    fund_name: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    due_date: Optional[str]
    error: Optional[str]
    created_at: datetime
        
    model_config = {"from_attributes": True}


# Optional fields, nullable - to prevent hallucination
# Null values also trigger escalation - human review queue
# Result Model for LLM
class ClassificationResult(BaseModel):
    doc_type: Optional[str] = None
    fund_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: Optional[str] = None
