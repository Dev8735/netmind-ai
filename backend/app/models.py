import os
import pandas as pd

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime


Base = declarative_base()


# ============================================================
# INCIDENT
# ============================================================

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    device_type = Column(String)
    incident_description = Column(Text)
    category = Column(String)
    priority = Column(String)
    symptoms = Column(Text)
    status = Column(String, default="Open")
    diagnosis_json = Column(Text)
    parent_incident_id = Column(Integer, nullable=True)
    remediation_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# KNOWLEDGE BASE
# ============================================================

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
    fault_type = Column(String)


# ============================================================
# ALERT
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    root_cause = Column(Text)
    evidence = Column(Text)
    solution_steps = Column(Text)
    message_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# REPORT
# ============================================================

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# SIGNAL
# ============================================================

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    device = Column(String)
    status = Column(String)
    message = Column(Text)
    incident_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# FEEDBACK
# ============================================================

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    helpful = Column(String)
    corrected_cause = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# NETWORK DEVICE
# ============================================================
#
# Represents physical/logical network devices:
#
#   Switch
#   Router
#   Firewall
#   Wireless AP
#   Server
#   Other SNMP-capable devices
#
# Port/interface count is NOT hard-coded here.
# Interfaces are discovered dynamically and stored separately.
# ============================================================

class NetworkDevice(Base):
    __tablename__ = "network_devices"

    id = Column(Integer, primary_key=True)

    # Human-readable device name
    name = Column(String, unique=True, nullable=False)

    # switch / router / firewall / access_point / server / other
    device_type = Column(String, nullable=False)

    # Cisco / HP / Aruba / Fortinet / etc.
    vendor = Column(String, nullable=True)

    # Optional hardware/model information
    model = Column(String, nullable=True)

    # Management IP address
    ip_address = Column(String, nullable=False)

    # SNMP UDP port
    snmp_port = Column(Integer, default=161)

    # SNMP v2c community for the lab/demo
    community = Column(String, default="public")

    # Current device state
    # ONLINE / OFFLINE / UNKNOWN
    status = Column(String, default="UNKNOWN")

    # Last successful SNMP poll
    last_seen = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# NETWORK INTERFACE
# ============================================================
#
# One row = one interface/port.
#
# This is deliberately dynamic:
#
# 16-port switch  -> 16 rows
# 24-port switch  -> 24 rows
# 48-port switch  -> 48 rows
# Router           -> whatever interfaces it exposes
# Firewall         -> whatever interfaces it exposes
#
# NetMind does NOT assume a fixed port count.
# ============================================================

class NetworkInterface(Base):
    __tablename__ = "network_interfaces"

    id = Column(Integer, primary_key=True)

    # Parent network device
    device_id = Column(
        Integer,
        ForeignKey("network_devices.id"),
        nullable=False,
    )

    # SNMP interface index
    if_index = Column(Integer, nullable=False)

    # Interface name, e.g.
    # Gi1/0/1
    # Gi1/0/24
    # eth0
    # Port1
    name = Column(String, nullable=False)

    # Optional interface description
    description = Column(Text, nullable=True)

    # Administrative state
    # UP / DOWN / UNKNOWN
    admin_status = Column(String, default="UNKNOWN")

    # Operational state
    # UP / DOWN / UNKNOWN
    oper_status = Column(String, default="UNKNOWN")

    # Interface speed in bits/sec
    speed = Column(Integer, nullable=True)

    # Traffic counters
    in_octets = Column(Integer, default=0)
    out_octets = Column(Integer, default=0)

    # Error counters
    in_errors = Column(Integer, default=0)
    out_errors = Column(Integer, default=0)

    # Last successful poll
    last_seen = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# DATABASE
# ============================================================

engine = create_engine(
    "sqlite:///../database/netmind.db"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():
    """
    Create missing tables.

    Existing tables/data are preserved.
    SQLAlchemy create_all() only creates tables that don't exist.
    """
    Base.metadata.create_all(engine)


# ============================================================
# KNOWLEDGE BASE LOADER
# ============================================================

def load_knowledge_base():
    Session = sessionmaker(bind=engine)
    session = Session()

    csv_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "knowledge_base.csv",
    )

    df = pd.read_csv(csv_path)

    existing_count = session.query(KnowledgeBase).count()

    if existing_count > 0:
        print(
            f"Knowledge base already has "
            f"{existing_count} entries. Skipping load."
        )

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
            business_impact=row["business_impact"],
            fault_type=(
                row.get("fault_type", "")
                if "fault_type" in df.columns
                else ""
            ),
        )

        session.add(kb_entry)

    session.commit()

    print(
        f"Loaded {len(df)} knowledge base entries."
    )

    session.close()