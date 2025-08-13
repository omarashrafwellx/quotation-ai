from sqlalchemy.orm import Session
from . import models
import uuid
import datetime
from typing import Dict, Any

# Broker operations
def get_broker_by_name(db: Session, name: str):
    return db.query(models.Broker).filter(models.Broker.name == name).first()

def get_broker_by_email(db: Session, email: str):
    return db.query(models.Broker).filter(models.Broker.email == email).first()

def create_broker(db: Session, name: str, email: str = None):
    db_broker = models.Broker(name=name, email=email)
    db.add(db_broker)
    db.commit()
    db.refresh(db_broker)
    return db_broker

def get_or_create_broker(db: Session, name: str, email: str = None):
    broker = get_broker_by_name(db, name)
    if not broker:
        broker = create_broker(db, name, email)
    return broker

# Relationship Manager operations
def get_relationship_manager_by_name(db: Session, name: str):
    return db.query(models.RelationshipManager).filter(models.RelationshipManager.name == name).first()

def create_relationship_manager(db: Session, name: str, email: str = None):
    db_rm = models.RelationshipManager(name=name, email=email)
    db.add(db_rm)
    db.commit()
    db.refresh(db_rm)
    return db_rm

def get_or_create_relationship_manager(db: Session, name: str, email: str = None):
    rm = get_relationship_manager_by_name(db, name)
    if not rm:
        rm = create_relationship_manager(db, name, email)
    return rm

# Quotation operations
def create_quotation(db: Session, client_name: str, broker_id: int, relationship_manager_id: int, 
                    request_email_id: str = None, broker_employee_id: int = None, 
                    policy_start_date: datetime.date = None,redis_task_id: str = None):
    # Generate a unique external ID
    today = datetime.datetime.now()
    external_id = f"QT-{today.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    db_quotation = models.Quotation(
        external_id=external_id,
        broker_id=broker_id,
        broker_employee_id=broker_employee_id,
        relationship_manager_id=relationship_manager_id,
        client_name=client_name,
        policy_start_date=policy_start_date,
        status=models.QuotationStatus.RECEIVED,
        request_email_id=request_email_id,
        redis_task_id=redis_task_id
    )
    db.add(db_quotation)
    db.commit()
    db.refresh(db_quotation)
    return db_quotation

def update_quotation_status(db: Session, quotation_id: int, status: models.QuotationStatus):
    db_quotation = db.query(models.Quotation).filter(models.Quotation.id == quotation_id).first()
    if db_quotation:
        db_quotation.status = status
        db.commit()
        db.refresh(db_quotation)
        return db_quotation
    return None

def update_quotation_pdf(db: Session, quotation_id: int, pdf_url: str):
    db_quotation = db.query(models.Quotation).filter(models.Quotation.id == quotation_id).first()
    if db_quotation:
        db_quotation.pdf_url = pdf_url
        db.commit()
        db.refresh(db_quotation)
        return db_quotation
    return None

def get_quotation_by_id(db: Session, quotation_id: int):
    return db.query(models.Quotation).filter(models.Quotation.id == quotation_id).first()

def get_quotation_by_external_id(db: Session, external_id: str):
    return db.query(models.Quotation).filter(models.Quotation.external_id == external_id).first()

def get_quotation_by_email_id(db: Session, email_id: str):
    return db.query(models.Quotation).filter(models.Quotation.request_email_id == email_id).first()

# Log operations
def create_log(db: Session, quotation_id: int, event_type: str, description: str = None, 
              request_data: Dict[str, Any] = None, response_data: Dict[str, Any] = None):
    db_log = models.Log(
        quotation_id=quotation_id,
        event_type=event_type,
        description=description,
        request_data=request_data,
        response_data=response_data
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_logs_for_quotation(db: Session, quotation_id: int):
    return db.query(models.Log).filter(models.Log.quotation_id == quotation_id).all()