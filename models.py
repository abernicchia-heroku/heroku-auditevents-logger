"""
SQLAlchemy models for the Heroku Audit Events Logger application.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()

class AuditEventsLog(Base):
    """Model for audit events log table"""
    __tablename__ = 'audit_events_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    process_date = Column(Date, nullable=False, unique=True)
    status = Column(String(20), nullable=False)
    events_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Define indexes for better query performance
    __table_args__ = (
        Index('idx_audit_events_log_status', 'status'),
        Index('idx_audit_events_log_process_date_status', 'process_date', 'status'),
    )
    
    def __repr__(self):
        return f"<AuditEventsLog(id={self.id}, process_date={self.process_date}, status='{self.status}')>"

class DatabaseManager:
    """Database manager for SQLAlchemy operations"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Create engine
        self.engine = create_engine(self.database_url, echo=False)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(bind=self.engine)
    
    def close(self):
        """Close the database engine"""
        self.engine.dispose()
