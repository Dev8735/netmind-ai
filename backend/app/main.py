import json
import os
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from dotenv import load_dotenv
from .models import engine, Incident, Signal, Feedback
from .nlp_parser import parse_incident_with_fallback as parse_incident
from .diagnosis_engine import diagnose_incident
from .alert_generator import generate_alert
from .report_generator import generate_pdf_report
from .auth import verify_password, create_access_token, ADMIN_USERNAME
from .remediation_engine import attempt_remediation, is_auto_remediable

load_dotenv()

app = FastAPI(title="NetMind AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

Session = sessionmaker(bind=engine)
active_connections = []

ESCALATION_MINUTES = 3


class IncidentCreate(BaseModel):
    text: str


class FeedbackCreate(BaseModel):
    helpful: str


class LoginRequest(BaseModel):
    username: str
    password: str


@app.websocket("/ws/incidents")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_message(payload: dict):
    for connection in active_connections[:]:
        try:
            await connection.send_json(payload)
        except Exception:
            if connection in active_connections:
                active_connections.remove(connection)


@app.on_event("startup")
async def startup_event():
    from . import syslog_listener
    syslog_listener.set_event_loop(asyncio.get_event_loop())
    syslog_listener.start_syslog_listener()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "NetMind AI backend"}


@app.post("/api/login")
def login(payload: LoginRequest):
    if payload.username != ADMIN_USERNAME or not verify_password(payload.password):
        return {"error": "Invalid credentials"}
    token = create_access_token(payload.username)
    return {"token": token}


@app.get("/api/incidents")
def get_incidents():
    session = Session()
    incidents = session.query(Incident).all()
    result = [
        {
            "id": i.id, "device": i.device_type, "issue": i.incident_description,
            "severity": i.priority, "status": i.status,
            "parent_incident_id": i.parent_incident_id
        }
        for i in incidents
    ]
    session.close()
    return result


@app.get("/api/signals")
def get_signals(limit: int = 20):
    session = Session()
    signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
    result = [
        {
            "id": s.id, "device": s.device, "status": s.status,
            "message": s.message, "incident_id": s.incident_id,
            "created_at": s.created_at.strftime("%H:%M:%S") if s.created_at else ""
        }
        for s in signals
    ]
    session.close()
    return result


@app.get("/api/analytics/recurring")
def get_recurring_faults():
    session = Session()
    incidents = session.query(Incident).all()
    session.close()

    counts = {}
    for i in incidents:
        key = f"{i.device_type} - {i.category}"
        counts[key] = counts.get(key, 0) + 1

    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_10 = sorted_counts[:10]

    return [{"label": label, "count": count} for label, count in top_10]


@app.get("/api/analytics/performance")
def get_performance_stats():
    session = Session()
    feedbacks = session.query(Feedback).all()
    incident_ids = [f.incident_id for f in feedbacks]
    incidents_map = {}
    if incident_ids:
        incidents_map = {
            i.id: i for i in session.query(Incident).filter(Incident.id.in_(incident_ids)).all()
        }
    session.close()

    total = len(feedbacks)
    helpful_yes = sum(1 for f in feedbacks if f.helpful == "yes")
    overall_accuracy = round((helpful_yes / total) * 100, 1) if total else None

    # Accuracy broken down by the confidence level the diagnosis engine
    # originally assigned - the most useful stat for judging whether
    # "high confidence" claims can actually be trusted.
    confidence_buckets = {}
    for f in feedbacks:
        incident = incidents_map.get(f.incident_id)
        if not incident or not incident.diagnosis_json:
            continue
        try:
            diagnosis = json.loads(incident.diagnosis_json)
        except (json.JSONDecodeError, TypeError):
            continue
        conf = diagnosis.get("confidence", "unknown")
        bucket = confidence_buckets.setdefault(conf, {"yes": 0, "total": 0})
        bucket["total"] += 1
        if f.helpful == "yes":
            bucket["yes"] += 1

    by_confidence = {
        level: round((data["yes"] / data["total"]) * 100, 1) if data["total"] else None
        for level, data in confidence_buckets.items()
    }

    # Accuracy trend by day, so improvements over time are visible.
    daily_buckets = {}
    for f in feedbacks:
        day = f.created_at.strftime("%Y-%m-%d") if f.created_at else "unknown"
        bucket = daily_buckets.setdefault(day, {"yes": 0, "total": 0})
        bucket["total"] += 1
        if f.helpful == "yes":
            bucket["yes"] += 1

    trend = [
        {
            "date": day,
            "accuracy": round((data["yes"] / data["total"]) * 100, 1) if data["total"] else 0,
            "count": data["total"]
        }
        for day, data in sorted(daily_buckets.items())
    ]

    return {
        "overall_accuracy": overall_accuracy,
        "total_feedback": total,
        "by_confidence": by_confidence,
        "trend": trend
    }


@app.get("/api/incidents/escalated")
def get_escalated_incidents():
    session = Session()
    cutoff = datetime.utcnow() - timedelta(minutes=ESCALATION_MINUTES)
    escalated = session.query(Incident).filter(
        Incident.priority == "Critical",
        Incident.status == "Open",
        Incident.created_at <= cutoff
    ).all()
    result = [{"id": i.id, "device": i.device_type} for i in escalated]
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
        "diagnosis": json.loads(incident.diagnosis_json) if incident.diagnosis_json else None,
        "remediation_log": incident.remediation_log
    }


@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int):
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        session.close()
        return {"error": "Not found"}
    incident.status = "Resolved"
    session.commit()
    session.close()
    return {"id": incident_id, "status": "Resolved"}


@app.post("/api/incidents/{incident_id}/feedback")
def submit_feedback(incident_id: int, payload: FeedbackCreate):
    session = Session()
    feedback = Feedback(incident_id=incident_id, helpful=payload.helpful)
    session.add(feedback)
    session.commit()
    session.close()
    return {"status": "recorded"}


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
    diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"], payload.text)

    incident_status = "Open"
    remediation_log = None
    if diagnosis["matched"] and diagnosis["confidence"] == "high":
        # Scan all ranked causes (not just the top one) for the first
        # cause whose fault_type is on the auto-remediation whitelist.
        # The top-ranked cause by embedding similarity is not always the
        # one that matches a remediable fault_type - a near-miss KB entry
        # (e.g. "port security violation") can outscore the correct
        # "port_admin_shutdown" entry on wording alone.
        remediable_cause = next(
            (c for c in diagnosis["causes"] if is_auto_remediable(c.get("fault_type", ""))),
            None
        )
        if remediable_cause:
            remediation = attempt_remediation(
                remediable_cause.get("fault_type", ""),
                remediable_cause["verification_command"]
            )
            if remediation:
                incident_status = "Auto-Resolved"
                remediation_log = remediation["log"]

    session = Session()
    new_incident = Incident(
        device_type=parsed["device"],
        incident_description=payload.text,
        category=parsed["category"],
        priority=diagnosis["severity"],
        symptoms=", ".join(parsed["keywords"][:5]),
        status=incident_status,
        diagnosis_json=json.dumps(diagnosis),
        remediation_log=remediation_log
    )
    session.add(new_incident)
    session.commit()
    session.refresh(new_incident)
    session.close()

    return {
        "id": new_incident.id,
        "message": "Incident created",
        "parsed": parsed,
        "diagnosis": diagnosis,
        "status": incident_status
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
            diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"], text)

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