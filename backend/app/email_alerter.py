import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

ALERT_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "sent_alerts.log")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# Obvious placeholder values from the .env.example template - if these are
# still present, there's no point attempting a real SMTP connection (it will
# just fail slowly). Skip straight to the file-log fallback instead.
PLACEHOLDER_MARKERS = ("your_real_email", "your16charapppassword", "example.com")


def _looks_like_placeholder(value: str) -> bool:
    if not value:
        return True
    return any(marker in value.lower() for marker in PLACEHOLDER_MARKERS)


def _log_to_file(subject: str, body: str, reason: str) -> None:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entry = (
        f"\n{'='*60}\n[{timestamp}] ALERT LOGGED (not emailed: {reason})\n"
        f"Subject: {subject}\n{'-'*60}\n{body}\n{'='*60}\n"
    )
    with open(ALERT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def send_alert_email(subject: str, body: str) -> dict:
    """
    Attempts to send a real alert email via SMTP (Gmail-compatible).
    Falls back to file logging if credentials are missing/placeholder,
    or if the SMTP send fails for any reason (auth, network, etc.).

    Always returns a status dict - never silently claims success when it
    didn't happen, matching the rest of this project's explainability
    principle: the caller (and eventually the UI) always knows exactly
    what happened, not just "done".

    Returns:
        {"sent": bool, "method": "smtp" | "file_log", "error": str | None}
    """
    sender = os.getenv("SENDER_EMAIL", "")
    app_password = os.getenv("SENDER_APP_PASSWORD", "")
    recipient = os.getenv("RECIPIENT_EMAIL", "")

    if _looks_like_placeholder(sender) or _looks_like_placeholder(app_password) or _looks_like_placeholder(recipient):
        _log_to_file(subject, body, "SMTP credentials not configured (.env still has placeholder values)")
        print(f"[email_alerter] Placeholder credentials detected, logged instead: {subject}")
        return {"sent": False, "method": "file_log", "error": "SMTP credentials not configured in .env"}

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], msg.as_string())

        print(f"[email_alerter] Email sent successfully: {subject}")
        return {"sent": True, "method": "smtp", "error": None}

    except smtplib.SMTPAuthenticationError as e:
        error_msg = (
            "SMTP authentication failed - check SENDER_EMAIL/SENDER_APP_PASSWORD in .env. "
            "For Gmail, this must be a 16-character App Password (Google Account > Security > "
            "App Passwords), not your regular account password, and 2-Step Verification must be enabled."
        )
        _log_to_file(subject, body, error_msg)
        print(f"[email_alerter] SMTP auth error, logged instead: {e}")
        return {"sent": False, "method": "file_log", "error": error_msg}

    except Exception as e:
        error_msg = f"SMTP send failed: {e}"
        _log_to_file(subject, body, error_msg)
        print(f"[email_alerter] {error_msg}, logged instead")
        return {"sent": False, "method": "file_log", "error": error_msg}