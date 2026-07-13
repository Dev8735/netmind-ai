import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from .models import engine, Incident
from .nlp_parser import parse_incident
from .diagnosis_engine import diagnose_incident

app = FastAPI(title="NetMind AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Session = sessionmaker(bind=engine)


class IncidentCreate(BaseModel):
    text: str


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "NetMind AI backend"}


@app.get("/api/incidents")
def get_incidents():
    session = Session()
    incidents = session.query(Incident).all()
    result = [
        {
            "id": i.id, "device": i.device_type, "issue": i.incident_description,
            "severity": i.priority, "status": i.status
        }
        for i in incidents
    ]
    session.close()
    return result


@app.get("/api/incidents/{incident_id}")
def get_incident_detail(incident_id: int):
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    session.close()
    if not incident:
        return {"error": "Not found"}
    return {
        "id": incident.id,
        "device": incident.device_type,
        "issue": incident.incident_description,
        "severity": incident.priority,
        "status": incident.status,
        "diagnosis": json.loads(incident.diagnosis_json) if incident.diagnosis_json else None
    }


@app.post("/api/incidents")
def create_incident(payload: IncidentCreate):
    parsed = parse_incident(payload.text)
    diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"])

    session = Session()
    new_incident = Incident(
        device_type=parsed["device"],
        incident_description=payload.text,
        category=parsed["category"],
        priority=diagnosis["severity"],
        symptoms=", ".join(parsed["keywords"][:5]),
        status="Open",
        diagnosis_json=json.dumps(diagnosis)
    )
    session.add(new_incident)
    session.commit()
    session.refresh(new_incident)
    session.close()

    return {
        "id": new_incident.id,
        "message": "Incident created",
        "parsed": parsed,
        "diagnosis": diagnosis
    }