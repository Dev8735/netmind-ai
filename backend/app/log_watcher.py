import os
import json
import threading
import time
from sqlalchemy.orm import sessionmaker
from .models import engine, Incident
from .nlp_parser import parse_incident
from .diagnosis_engine import diagnose_incident

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "simulator", "live_logs.txt")
Session = sessionmaker(bind=engine)

_last_position = 0
_watcher_running = False


def _process_new_line(line: str):
    text = line.strip()
    if not text:
        return

    if "]" in text:
        text = text.split("]", 1)[1].strip()

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
    session.close()
    print(f"[log_watcher] Auto-created incident: {parsed['device']} - {diagnosis['severity']}")


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