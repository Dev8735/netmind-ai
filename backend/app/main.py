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
from .models import engine, Incident, Signal, Feedback, KnowledgeBase
from .nlp_parser import parse_incident_with_fallback as parse_incident
from .diagnosis_engine import diagnose_incident
from .alert_generator import generate_alert
from .report_generator import generate_pdf_report
from .auth import verify_password, create_access_token, ADMIN_USERNAME
from .remediation_engine import attempt_remediation, is_auto_remediable
from .conversation_engine import answer_question
from .email_alerter import send_alert_email

load_dotenv()


def get_top_fault_type(diagnosis_json):
    """Extract the fault_type of the top-ranked cause from a stored
    diagnosis_json string. Returns None if there's no match, no causes,
    or the top cause has no fault_type tagged."""
    if not diagnosis_json:
        return None
    try:
        diagnosis = json.loads(diagnosis_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not diagnosis.get("matched") or not diagnosis.get("causes"):
        return None
    fault_type = diagnosis["causes"][0].get("fault_type")
    return fault_type or None

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
    corrected_cause: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminVerifyRequest(BaseModel):
    password: str


class AskQuestionRequest(BaseModel):
    question: str


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


@app.post("/api/admin/verify")
def verify_admin_panel(payload: AdminVerifyRequest):
    # Separate, independent secret from the main app login - gates access
    # to internal/explainability tooling (pipeline diagram, decision tree,
    # knowledge graph) that isn't needed for day-to-day incident triage.
    # Set ADMIN_PANEL_PASSWORD in backend/.env to override the default.
    expected = os.getenv("ADMIN_PANEL_PASSWORD", "netmind_admin")
    if payload.password != expected:
        return {"valid": False}
    return {"valid": True}


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


@app.get("/api/knowledge-base/symptom-groups")
def get_symptom_groups():
    """Distinct symptom groups from the knowledge base, each of which may
    branch into multiple ranked possible causes - the raw material for the
    decision tree explorer."""
    session = Session()
    entries = session.query(KnowledgeBase).all()
    session.close()

    groups = {}
    for e in entries:
        key = e.incident_description
        groups[key] = groups.get(key, 0) + 1

    result = [{"symptom": symptom, "cause_count": count} for symptom, count in groups.items()]
    result.sort(key=lambda x: x["cause_count"], reverse=True)
    return result


@app.get("/api/knowledge-base/tree")
def get_decision_tree(symptom: str):
    """Build a branching decision tree for one symptom group: root =
    the symptom text, children = each possible cause ranked by
    probability, with its verification command and troubleshooting
    steps as leaf detail."""
    session = Session()
    entries = session.query(KnowledgeBase).filter(KnowledgeBase.incident_description == symptom).all()
    session.close()

    causes = []
    for e in entries:
        try:
            probability = int(e.probability)
        except (TypeError, ValueError):
            probability = 0
        causes.append({
            "cause": e.possible_cause,
            "probability": probability,
            "verification_command": e.verification_command,
            "troubleshooting_steps": e.troubleshooting_steps,
            "severity": e.severity,
            "fault_type": e.fault_type or None,
        })

    causes.sort(key=lambda x: x["probability"], reverse=True)
    return {"symptom": symptom, "causes": causes}


@app.get("/api/knowledge-graph")
def get_knowledge_graph():
    """Build a device <-> fault_type relationship graph from real
    diagnosed incident history: which devices have actually been
    diagnosed with which fault types, and how often. This surfaces
    patterns not visible in any single incident or symptom tree -
    e.g. a fault type showing up across multiple device types."""
    session = Session()
    incidents = session.query(Incident).all()
    session.close()

    device_counts = {}
    fault_counts = {}
    edge_counts = {}

    for incident in incidents:
        fault_type = get_top_fault_type(incident.diagnosis_json)
        if not fault_type:
            continue
        device = incident.device_type
        device_counts[device] = device_counts.get(device, 0) + 1
        fault_counts[fault_type] = fault_counts.get(fault_type, 0) + 1
        edge_key = (device, fault_type)
        edge_counts[edge_key] = edge_counts.get(edge_key, 0) + 1

    nodes = (
        [{"id": f"device:{d}", "type": "device", "label": d, "count": c} for d, c in device_counts.items()] +
        [{"id": f"fault:{f}", "type": "fault_type", "label": f, "count": c} for f, c in fault_counts.items()]
    )
    edges = [
        {"source": f"device:{d}", "target": f"fault:{f}", "weight": w}
        for (d, f), w in edge_counts.items()
    ]

    return {"nodes": nodes, "edges": edges}


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


@app.get("/api/corrections")
def get_corrections():
    """Learning Mode log: every piece of feedback where an engineer
    marked a diagnosis unhelpful and specified what the actual cause
    was. Shows what the AI originally said vs what was correct, so
    this becomes visible, demonstrable evidence the system captures
    its own mistakes rather than a black-box accuracy number."""
    session = Session()
    corrections = (
        session.query(Feedback)
        .filter(Feedback.helpful == "no", Feedback.corrected_cause.isnot(None))
        .order_by(Feedback.created_at.desc())
        .all()
    )
    incident_ids = [c.incident_id for c in corrections]
    incidents_map = {}
    if incident_ids:
        incidents_map = {
            i.id: i for i in session.query(Incident).filter(Incident.id.in_(incident_ids)).all()
        }
    session.close()

    results = []
    for c in corrections:
        incident = incidents_map.get(c.incident_id)
        if not incident:
            continue
        original_cause = None
        if incident.diagnosis_json:
            try:
                diagnosis = json.loads(incident.diagnosis_json)
                if diagnosis.get("matched") and diagnosis.get("causes"):
                    original_cause = diagnosis["causes"][0].get("cause")
            except (json.JSONDecodeError, TypeError):
                pass
        results.append({
            "incident_id": c.incident_id,
            "device": incident.device_type,
            "issue": incident.incident_description,
            "ai_said": original_cause,
            "corrected_to": c.corrected_cause,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
        })

    return {"total": len(results), "corrections": results}


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


@app.get("/api/incidents/search")
def search_similar_incidents(text: str):
    parsed = parse_incident(text)
    diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"], text)

    fault_type = None
    if diagnosis.get("matched") and diagnosis.get("causes"):
        fault_type = diagnosis["causes"][0].get("fault_type") or None

    session = Session()
    all_incidents = session.query(Incident).all()
    session.close()

    if fault_type:
        matched = [
            {
                "id": i.id,
                "device": i.device_type,
                "issue": i.incident_description,
                "severity": i.priority,
                "status": i.status,
                "created_at": i.created_at.strftime("%Y-%m-%d %H:%M") if i.created_at else ""
            }
            for i in all_incidents if get_top_fault_type(i.diagnosis_json) == fault_type
        ]
        match_basis = "fault_type"
    else:
        matched = [
            {
                "id": i.id,
                "device": i.device_type,
                "issue": i.incident_description,
                "severity": i.priority,
                "status": i.status,
                "created_at": i.created_at.strftime("%Y-%m-%d %H:%M") if i.created_at else ""
            }
            for i in all_incidents if i.category == parsed["category"]
        ]
        match_basis = "category"

    matched.sort(key=lambda x: x["created_at"], reverse=True)
    return {
        "query_diagnosis": diagnosis,
        "fault_type": fault_type,
        "match_basis": match_basis,
        "results": matched[:10]
    }


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


@app.get("/api/incidents/{incident_id}/similar")
def get_similar_incidents(incident_id: int):
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        session.close()
        return {"error": "Not found"}

    fault_type = get_top_fault_type(incident.diagnosis_json)
    if not fault_type:
        session.close()
        return {"fault_type": None, "similar": []}

    others = session.query(Incident).filter(Incident.id != incident_id).all()
    session.close()

    similar = []
    for other in others:
        if get_top_fault_type(other.diagnosis_json) == fault_type:
            similar.append({
                "id": other.id,
                "device": other.device_type,
                "issue": other.incident_description,
                "severity": other.priority,
                "status": other.status,
                "created_at": other.created_at.strftime("%Y-%m-%d %H:%M") if other.created_at else ""
            })

    similar.sort(key=lambda x: x["created_at"], reverse=True)
    return {"fault_type": fault_type, "similar": similar[:10]}


PHYSICAL_ATTENTION_MARKERS = (
    "physical inspection", "physical cable", "cable", "power cable",
    "power supply", "psu", "circuit breaker", "hardware", "faulty sfp",
    "faulty transceiver", "replace"
)


def _requires_physical_attention(cause: dict) -> bool:
    text = f"{cause.get('verification_command', '')} {cause.get('cause', '')} {cause.get('troubleshooting_steps', '')}".lower()
    return any(marker in text for marker in PHYSICAL_ATTENTION_MARKERS)


@app.post("/api/incidents/{incident_id}/start-resolving")
def start_resolving(incident_id: int):
    """Engineer-triggered resolution attempt. Three possible outcomes:
    1. Safe, whitelisted fault type -> auto-remediated immediately (same
       whitelist as automatic remediation at incident creation).
    2. Top cause requires physical intervention (cable, PSU, hardware) ->
       cannot be resolved remotely, so an Admin Alert is auto-generated
       to flag it for someone with physical access.
    3. Otherwise -> marked In Progress, troubleshooting steps returned
       for the engineer to follow manually."""
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        session.close()
        return {"error": "Not found"}

    diagnosis = json.loads(incident.diagnosis_json) if incident.diagnosis_json else None
    top_cause = None
    if diagnosis and diagnosis.get("matched") and diagnosis.get("causes"):
        top_cause = diagnosis["causes"][0]

    if not top_cause:
        session.close()
        return {
            "action": "manual_review",
            "message": "No confident diagnosis available - this requires manual investigation from scratch."
        }

    fault_type = top_cause.get("fault_type", "")

    # Outcome 1: safe, whitelisted, config-only fix.
    if is_auto_remediable(fault_type):
        remediation = attempt_remediation(fault_type, top_cause["verification_command"])
        if remediation:
            incident.status = "Auto-Resolved"
            incident.remediation_log = remediation["log"]
            session.commit()
            session.close()
            return {
                "action": "resolved",
                "status": "Auto-Resolved",
                "remediation_log": remediation["log"]
            }

    # Outcome 2: needs a human with physical access - auto-generate the alert.
    if _requires_physical_attention(top_cause):
        alert_text = generate_alert(incident.device_type, incident.incident_description, diagnosis)
        incident.status = "Escalated - Physical Attention Required"
        session.commit()
        session.close()
        return {
            "action": "escalated",
            "status": "Escalated - Physical Attention Required",
            "alert_text": alert_text
        }

    # Outcome 3: neither auto-fixable nor physical - engineer follows the steps.
    incident.status = "In Progress"
    session.commit()
    session.close()
    return {
        "action": "in_progress",
        "status": "In Progress",
        "cause": top_cause["cause"],
        "verification_command": top_cause["verification_command"],
        "troubleshooting_steps": top_cause["troubleshooting_steps"]
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
    feedback = Feedback(
        incident_id=incident_id,
        helpful=payload.helpful,
        corrected_cause=payload.corrected_cause
    )
    session.add(feedback)
    session.commit()
    session.close()
    return {"status": "recorded"}


@app.post("/api/incidents/{incident_id}/ask")
def ask_about_incident(incident_id: int, payload: AskQuestionRequest):
    """Scoped Q&A: answers are grounded only in this incident's own
    diagnosis (causes, evidence, remediation) plus its similar past
    incidents - not general knowledge. Uses Ollama when available,
    falls back to rule-based canned answers otherwise."""
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        session.close()
        return {"error": "Not found"}

    diagnosis = json.loads(incident.diagnosis_json) if incident.diagnosis_json else None

    fault_type = get_top_fault_type(incident.diagnosis_json)
    similar_incidents = []
    if fault_type:
        others = session.query(Incident).filter(Incident.id != incident_id).all()
        for other in others:
            if get_top_fault_type(other.diagnosis_json) == fault_type:
                similar_incidents.append({"device": other.device_type, "status": other.status})
    session.close()

    answer = answer_question(payload.question, diagnosis, similar_incidents)
    return {"answer": answer}


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


@app.post("/api/incidents/{incident_id}/send-alert-email")
def send_incident_alert_email(incident_id: int):
    """Manually trigger the alert email for an incident. Always returns
    a status dict (sent via real SMTP, or logged to file with the reason)
    - never silently claims success."""
    session = Session()
    incident = session.query(Incident).filter(Incident.id == incident_id).first()
    session.close()
    if not incident:
        return {"error": "Not found"}

    diagnosis = json.loads(incident.diagnosis_json) if incident.diagnosis_json else None
    alert_text = generate_alert(incident.device_type, incident.incident_description, diagnosis)
    subject = f"NetMind AI Alert - {incident.priority} - {incident.device_type}"

    result = send_alert_email(subject, alert_text)
    return result


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

    # Automatic email alert for High/Critical severity incidents. Wrapped
    # in try/except so a slow or failing email (network issues, bad
    # credentials) can never break incident creation itself - the incident
    # is already safely committed to the DB above this point regardless
    # of what happens here.
    email_result = None
    if diagnosis["severity"] in ("High", "Critical"):
        try:
            alert_text = generate_alert(parsed["device"], payload.text, diagnosis)
            subject = f"NetMind AI Alert - {diagnosis['severity']} - {parsed['device']}"
            email_result = send_alert_email(subject, alert_text)
        except Exception as e:
            print(f"[create_incident] Auto-alert email failed unexpectedly: {e}")
            email_result = {"sent": False, "method": "file_log", "error": str(e)}

    return {
        "id": new_incident.id,
        "message": "Incident created",
        "parsed": parsed,
        "diagnosis": diagnosis,
        "status": incident_status,
        "email_alert": email_result
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