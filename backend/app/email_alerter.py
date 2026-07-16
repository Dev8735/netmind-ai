import os
from datetime import datetime

ALERT_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "sent_alerts.log")


def send_alert_email(subject: str, body: str) -> bool:
    """
    Simulates sending an alert by logging it to a file.
    This demonstrates the automated alerting trigger without requiring
    real email credentials - swap in real SMTP later if desired.
    """
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"\n{'='*60}\n[{timestamp}] ALERT SENT\nSubject: {subject}\n{'-'*60}\n{body}\n{'='*60}\n"

        with open(ALERT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)

        print(f"[email_alerter] Alert logged: {subject}")
        return True
    except Exception as e:
        print(f"[email_alerter] Failed to log alert: {e}")
        return False