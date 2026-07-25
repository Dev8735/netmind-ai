import socket
import threading
import json
import re
import asyncio
from sqlalchemy.orm import sessionmaker
from .models import engine, Incident, Signal
from .nlp_parser import parse_incident_with_fallback as parse_incident
from .diagnosis_engine import diagnose_incident
from .email_alerter import send_alert_email
from .correlation_engine import find_correlated_parent
from .remediation_engine import attempt_remediation

Session = sessionmaker(bind=engine)

SYSLOG_HOST = "127.0.0.1"
SYSLOG_PORT = 5140

_main_loop = None
_listener_started = False

SYSLOG_PATTERN = re.compile(r'^<(\d+)>1\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+(?:-|\[.*?\])\s+(.*)$')


def set_event_loop(loop):
    global _main_loop
    _main_loop = loop


def _notify_dashboard(payload: dict):
    if _main_loop is None:
        return
    from .main import broadcast_message
    asyncio.run_coroutine_threadsafe(broadcast_message(payload), _main_loop)


def _process_signal(device: str, status: str, message: str):
    session = Session()

    if status == "OK":
        signal = Signal(device=device, status="ok", message=message, incident_id=None)
        session.add(signal)
        session.commit()
        session.close()
        print(f"[syslog_listener] Signal OK: {device}")
        _notify_dashboard({"type": "signal", "device": device, "status": "ok", "message": message})
        return

    parsed = parse_incident(message)
    diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"], message)
    incident_device = parsed["device"] if parsed["device"] != "Unknown" else device

    parent_id = find_correlated_parent(incident_device, parsed["category"])

    incident_status = "Open"
    remediation_log = None
    if diagnosis["matched"] and diagnosis["confidence"] == "high":
        top_cause = diagnosis["causes"][0]
        remediation = attempt_remediation(top_cause.get("fault_type", ""), top_cause["verification_command"])
        if remediation:
            incident_status = "Auto-Resolved"
            remediation_log = remediation["log"]

    incident = Incident(
        device_type=incident_device,
        incident_description=message,
        category=parsed["category"],
        priority=diagnosis["severity"],
        symptoms=", ".join(parsed["keywords"][:5]),
        status=incident_status,
        diagnosis_json=json.dumps(diagnosis),
        parent_incident_id=parent_id,
        remediation_log=remediation_log
    )
    session.add(incident)
    session.commit()
    incident_id = incident.id

    signal = Signal(device=device, status="fault", message=message, incident_id=incident_id)
    session.add(signal)
    session.commit()
    session.close()

    print(f"[syslog_listener] Auto-created incident via Syslog: {incident_device} - {diagnosis['severity']} ({incident_status})")
    if parent_id:
        print(f"[syslog_listener] Incident {incident_id} correlated under parent {parent_id}")

    _notify_dashboard({
        "type": "incident",
        "id": incident_id, "device": incident_device, "issue": message,
        "severity": diagnosis["severity"], "status": incident_status,
        "parent_incident_id": parent_id
    })
    _notify_dashboard({"type": "signal", "device": device, "status": "fault", "message": message})

    if diagnosis["severity"] in ["Critical", "High"]:
        subject = f"[NetMind AI] {diagnosis['severity']} Incident - {incident_device}"
        body = f"Device: {incident_device}\nSeverity: {diagnosis['severity']}\nIssue: {message}\n\nCheck the dashboard for full diagnosis."
        send_alert_email(subject, body)


def _parse_syslog_message(raw: str):
    """
    Parses a simplified RFC 5424 Syslog message.
    Expected MSG portion format: device|STATUS|message
    """
    match = SYSLOG_PATTERN.match(raw)
    if not match:
        return None

    msg_part = match.group(2)
    parts = msg_part.split("|", 2)
    if len(parts) < 3:
        return None

    device, status, message = parts
    return device, status, message


def _listen_loop():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SYSLOG_HOST, SYSLOG_PORT))
    print(f"[syslog_listener] Listening for Syslog (RFC 5424) messages on udp://{SYSLOG_HOST}:{SYSLOG_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            raw = data.decode("utf-8", errors="ignore").strip()
            parsed = _parse_syslog_message(raw)
            if parsed:
                device, status, message = parsed
                _process_signal(device, status, message)
            else:
                print(f"[syslog_listener] Could not parse message: {raw[:100]}")
        except Exception as e:
            print(f"[syslog_listener] Error: {e}")


def start_syslog_listener():
    global _listener_started
    if _listener_started:
        return
    _listener_started = True
    thread = threading.Thread(target=_listen_loop, daemon=True)
    thread.start()