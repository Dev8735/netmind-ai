from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    device_type = Column(String)
    incident_description = Column(Text)
    category = Column(String)
    priority = Column(String)
    symptoms = Column(Text)
    status = Column(String, default="Open")
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"
    id = Column(Integer, primary_key=True)
    incident_description = Column(Text)
    symptoms = Column(Text)
    possible_cause = Column(Text)
    probability = Column(String)
    verification_command = Column(Text)
    troubleshooting_steps = Column(Text)
    severity = Column(String)
    business_impact = Column(Text)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    root_cause = Column(Text)
    evidence = Column(Text)
    solution_steps = Column(Text)
    message_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine("sqlite:///../database/netmind.db")

def init_db():
    Base.metadata.create_all(engine)

import pandas as pd
import os
from sqlalchemy.orm import sessionmaker


def load_knowledge_base():
    Session = sessionmaker(bind=engine)
    session = Session()

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.csv")
    df = pd.read_csv(csv_path)

    existing_count = session.query(KnowledgeBase).count()
    if existing_count > 0:
        print(f"Knowledge base already has {existing_count} entries. Skipping load.")
        session.close()
        return

    for _, row in df.iterrows():
        kb_entry = KnowledgeBase(
            incident_description=row["incident_description"],
            symptoms=row["symptoms"],
            possible_cause=row["possible_cause"],
            probability=str(row["probability"]),
            verification_command=row["verification_command"],
            troubleshooting_steps=row["troubleshooting_steps"],
            severity=row["severity"],
            business_impact=row["business_impact"]
        )
        session.add(kb_entry)

    session.commit()
    print(f"Loaded {len(df)} knowledge base entries.")
    session.close()