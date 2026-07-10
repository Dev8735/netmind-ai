from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from .models import engine, Incident

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


@app.post("/api/incidents")
def create_incident(payload: IncidentCreate):
    session = Session()
    new_incident = Incident(
        device_type="Unknown",
        incident_description=payload.text,
        category="Uncategorized",
        priority="Medium",
        symptoms="",
        status="Open"
    )
    session.add(new_incident)
    session.commit()
    session.refresh(new_incident)
    session.close()
    return {"id": new_incident.id, "message": "Incident created"}