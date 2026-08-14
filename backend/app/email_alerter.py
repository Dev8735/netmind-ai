import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

from dotenv import load_dotenv

# ============================================================
# LOAD .ENV
# ============================================================
# .env location:
# C:\Internship\netmind-ai\backend\.env
#
# This file is located one level above this module:
# C:\Internship\netmind-ai\backend\app\email_alerter.py
# ============================================================

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

ENV_FILE = os.path.join(BACKEND_DIR, ".env")

load_dotenv(ENV_FILE)

# ============================================================
# EMAIL CONFIGURATION
# ============================================================

ALERT_LOG_FILE = os.path.join(
    BACKEND_DIR,
    "sent_alerts.log"
)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD", "").strip()
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "").strip()

# Values that indicate the .env still contains examples.
PLACEHOLDER_MARKERS = (
    "your_real_email",
    "your16charapppassword",
    "example.com",
)


def _looks_like_placeholder(value: str) -> bool:
    if not value:
        return True

    value_lower = value.lower()

    return any(
        marker in value_lower
        for marker in PLACEHOLDER_MARKERS
    )


def _log_to_file(
        subject: str,
        body: str,
        reason: str
) -> None:
    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    entry = (
        f"\n{'=' * 60}\n"
        f"[{timestamp}] ALERT LOGGED "
        f"(not emailed: {reason})\n"
        f"Subject: {subject}\n"
        f"{'-' * 60}\n"
        f"{body}\n"
        f"{'=' * 60}\n"
    )

    with open(
            ALERT_LOG_FILE,
            "a",
            encoding="utf-8"
    ) as f:
        f.write(entry)


def send_alert_email(
        subject: str,
        body: str
) -> dict:
    """
    Send an alert email through Gmail SMTP.

    Returns:
        {
            "sent": bool,
            "method": "smtp" | "file_log",
            "error": str | None
        }
    """

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if (
            _looks_like_placeholder(SENDER_EMAIL)
            or _looks_like_placeholder(SENDER_APP_PASSWORD)
            or _looks_like_placeholder(RECIPIENT_EMAIL)
    ):
        reason = (
            "SMTP credentials missing or still contain "
            "placeholder values in backend/.env"
        )

        _log_to_file(
            subject,
            body,
            reason
        )

        print(
            "[email_alerter] SMTP configuration missing. "
            f"Logged instead: {subject}"
        )

        return {
            "sent": False,
            "method": "file_log",
            "error": reason
        }

    # --------------------------------------------------------
    # Create and send email
    # --------------------------------------------------------

    try:
        msg = MIMEText(
            body,
            "plain",
            "utf-8"
        )

        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL

        with smtplib.SMTP(
                SMTP_HOST,
                SMTP_PORT,
                timeout=15
        ) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()

            server.login(
                SENDER_EMAIL,
                SENDER_APP_PASSWORD
            )

            server.sendmail(
                SENDER_EMAIL,
                [RECIPIENT_EMAIL],
                msg.as_string()
            )

        print(
            "[email_alerter] Email sent successfully: "
            f"{subject}"
        )

        return {
            "sent": True,
            "method": "smtp",
            "error": None
        }

    except smtplib.SMTPAuthenticationError as e:
        error_msg = (
            "Gmail SMTP authentication failed. "
            "Check SENDER_EMAIL and SENDER_APP_PASSWORD. "
            "SENDER_APP_PASSWORD must be a Gmail App Password, "
            "not the normal Gmail account password."
        )

        _log_to_file(
            subject,
            body,
            error_msg
        )

        print(
            "[email_alerter] SMTP authentication failed: "
            f"{e}"
        )

        return {
            "sent": False,
            "method": "file_log",
            "error": error_msg
        }

    except Exception as e:
        error_msg = (
            f"SMTP send failed: {type(e).__name__}: {e}"
        )

        _log_to_file(
            subject,
            body,
            error_msg
        )

        print(
            f"[email_alerter] {error_msg}"
        )

        return {
            "sent": False,
            "method": "file_log",
            "error": error_msg
        }
