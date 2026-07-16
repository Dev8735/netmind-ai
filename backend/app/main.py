import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from .models import engine, Incident
from .nlp_parser import parse_incident
from .diagnosis_engine import diagnose_incident
from .alert_generator import generate_alert
from .report_generator import generate_pdf_report

app = FastAPI(title="NetMind AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
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


@app.get("/api/incidents/{incident_id}/alert")
def get_incident_alert(incident_id: int):
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    session.close()
    if not incident:
        return {"error": "Not found"}

    diagnosis = json.loads(incident.diagnosis_json) if incident.diagnosis_json else None
    alert_text = generate_alert(incident.device_type, incident.incident_description, diagnosis)
    return {"alert": alert_text}


@app.get("/api/incidents/{incident_id}/report")
def download_report(incident_id: int):
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    session.close()
    if not incident:
        return {"error": "Not found"}

    diagnosis = json.loads(incident.diagnosis_json) if incident.diagnosis_json else None
    alert_text = generate_alert(incident.device_type, incident.incident_description, diagnosis)

    output_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    filepath = generate_pdf_report(incident, diagnosis, alert_text, output_dir)

    return FileResponse(filepath, media_type='application/pdf',
                         filename=f"NetMind_Report_Incident_{incident_id}.pdf")


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


TEST_INCIDENTS = [
    "Core switch has no LEDs on and is not responding to ping",
    "Users complaining about slow internet, router CPU is at 95%",
    "Wifi on 3rd floor keeps disconnecting every few minutes",
    "Port 12 on switch keeps going up and down in the logs",
    "BGP neighbor to ISP router is down",
    "New laptop not getting an IP address from DHCP",
    "VPN tunnel to branch office keeps dropping",
    "Firewall is blocking access to the internal portal",
    "Printer not responding to any print jobs",
    "Something strange is happening with the network, not sure what",
]


@app.post("/api/run-tests")
def run_tests():
    results = []
    for text in TEST_INCIDENTS:
        result = {"text": text, "status": "PASS"}
        try:
            parsed = parse_incident(text)
            diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"])

            session = Session()
            incident = Incident(
                device_type=parsed["device"],
                incident_description=text,
                category=parsed["category"],
                priority=diagnosis["severity"],
                symptoms=", ".join(parsed["keywords"][:5]),
                status="Open",
                diagnosis_json=json.dumps(diagnosis)
            )
            session.add(incident)
            session.commit()
            session.refresh(incident)
            session.close()

            alert_text = generate_alert(incident.device_type, incident.incident_description, diagnosis)
            output_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
            generate_pdf_report(incident, diagnosis, alert_text, output_dir)

            result["device"] = parsed["device"]
            result["severity"] = diagnosis["severity"]
            result["matched"] = diagnosis["matched"]
        except Exception as e:
            result["status"] = "FAIL"
            result["error"] = str(e)
        results.append(result)

    passed = sum(1 for r in results if r["status"] == "PASS")
    return {"results": results, "passed": passed, "total": len(results)}