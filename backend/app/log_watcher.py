import os
import json
import threading
import time
import asyncio
from sqlalchemy.orm import sessionmaker
from .models import engine, Incident, Signal
from .nlp_parser import parse_incident_with_fallback as parse_incident
from .diagnosis_engine import diagnose_incident
from .email_alerter import send_alert_email

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "simulator", "live_logs.txt")
Session = sessionmaker(bind=engine)

_last_position = 0
_watcher_running = False
_main_loop = None


def set_event_loop(loop):
    global _main_loop
    _main_loop = loop


def _notify_dashboard(payload: dict):
    if _main_loop is None:
        return
    from .main import broadcast_message
    asyncio.run_coroutine_threadsafe(broadcast_message(payload), _main_loop)


def _process_new_line(line: str):
    text = line.strip()
    if not text:
        return

    if "]" in text:
        text = text.split("]", 1)[1].strip()

    if not text.startswith("SIGNAL|"):
        return

    parts = text.split("|", 3)
    if len(parts) < 4:
        return
    _, status, device, message = parts

    session = Session()

    if status == "OK":
        signal = Signal(device=device, status="ok", message=message, incident_id=None)
        session.add(signal)
        session.commit()
        session.close()
        print(f"[log_watcher] Signal OK: {device}")
        _notify_dashboard({"type": "signal", "device": device, "status": "ok", "message": message})
        return

    parsed = parse_incident(message)
    diagnosis = diagnose_incident(parsed["device"], parsed["category"], parsed["keywords"], message)

    incident_device = parsed["device"] if parsed["device"] != "Unknown" else device

    incident = Incident(
        device_type=incident_device,
        incident_description=message,
        category=parsed["category"],
        priority=diagnosis["severity"],
        symptoms=", ".join(parsed["keywords"][:5]),
        status="Open",
        diagnosis_json=json.dumps(diagnosis)
    )
    session.add(incident)
    session.commit()
    incident_id = incident.id

    signal = Signal(device=device, status="fault", message=message, incident_id=incident_id)
    session.add(signal)
    session.commit()
    session.close()

    print(f"[log_watcher] Auto-created incident: {incident_device} - {diagnosis['severity']}")

    _notify_dashboard({
        "type": "incident",
        "id": incident_id, "device": incident_device, "issue": message,
        "severity": diagnosis["severity"], "status": "Open"
    })
    _notify_dashboard({"type": "signal", "device": device, "status": "fault", "message": message})

    if diagnosis["severity"] in ["Critical", "High"]:
        subject = f"[NetMind AI] {diagnosis['severity']} Incident - {incident_device}"
        body = f"Device: {incident_device}\nSeverity: {diagnosis['severity']}\nIssue: {message}\n\nCheck the dashboard for full diagnosis."
        send_alert_email(subject, body)


def _watch_loop():
    global _last_position
    print("[log_watcher] Started watching for new log entries...")

    while True:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                f.seek(_last_position)
                new_lines = f.readlines()
                _last_position = f.tell()

            for line in new_lines:
                try:
                    _process_new_line(line)
                except Exception as e:
                    print(f"[log_watcher] Error processing line: {e}")

        time.sleep(5)


def start_watcher():
    global _watcher_running
    if _watcher_running:
        return
    _watcher_running = True
    thread = threading.Thread(target=_watch_loop, daemon=True)
    thread.start()