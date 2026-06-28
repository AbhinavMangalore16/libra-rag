from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class IngestedDocument(Base):
    __tablename__ = "ingested_documents"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, index=True)
    user_id = Column(String, index=True)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

class QueryLog(Base):
    __tablename__ = "query_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True)
    user_id = Column(String, index=True, nullable=True)
    query = Column(Text)
    answer = Column(Text)
    route = Column(String)
    eval_metrics = Column(JSON, default={})
    timestamp = Column(DateTime, default=datetime.utcnow)
