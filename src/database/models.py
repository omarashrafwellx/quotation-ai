from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum
from .database import Base

# Define Enum for Quotation Status
class QuotationStatus(enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"

class Broker(Base):
    __tablename__ = "brokers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    employees = relationship("BrokerEmployee", back_populates="broker", cascade="all, delete-orphan")
    quotations = relationship("Quotation", back_populates="broker", cascade="all, delete-orphan")

class BrokerEmployee(Base):
    __tablename__ = "broker_employees"
    
    id = Column(Integer, primary_key=True)
    broker_id = Column(Integer, ForeignKey("brokers.id"))
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    broker = relationship("Broker", back_populates="employees")
    quotations = relationship("Quotation", back_populates="broker_employee", cascade="all, delete-orphan")

class RelationshipManager(Base):
    __tablename__ = "relationship_managers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    quotations = relationship("Quotation", back_populates="relationship_manager", cascade="all, delete-orphan")

class Quotation(Base):
    __tablename__ = "quotations"
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(255), unique=True)
    broker_id = Column(Integer, ForeignKey("brokers.id"))
    broker_employee_id = Column(Integer, ForeignKey("broker_employees.id"), nullable=True)
    relationship_manager_id = Column(Integer, ForeignKey("relationship_managers.id"))
    client_name = Column(String(255), nullable=False)
    quote_amount = Column(Numeric(15, 2), nullable=True)
    policy_start_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(QuotationStatus), default=QuotationStatus.RECEIVED)
    pdf_url = Column(String(1024), nullable=True)
    redis_task_id = Column(String(255), nullable=True)
    request_email_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    broker = relationship("Broker", back_populates="quotations")
    broker_employee = relationship("BrokerEmployee", back_populates="quotations")
    relationship_manager = relationship("RelationshipManager", back_populates="quotations")
    logs = relationship("Log", back_populates="quotation", cascade="all, delete-orphan")

class Log(Base):
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"))
    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    request_data = Column(JSONB, nullable=True)
    response_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    quotation = relationship("Quotation", back_populates="logs")