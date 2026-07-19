import random
import socket
import time
from datetime import datetime, timezone

DEVICES = ["Core-Switch-01", "Router-Branch-02", "AP-Floor3-05", "Firewall-Edge-01", "Switch-Server-Room"]

FAULT_SCENARIOS = [
    "{device} not responding to ping, LEDs off",
    "{device} showing high CPU usage causing slow performance",
    "{device} port flapping repeatedly in logs",
    "{device} administratively shut down by configuration",
    "{device} cable appears disconnected, link down",
    "{device} wifi clients experiencing intermittent drops",
    "{device} BGP neighbor session down",
    "{device} DHCP pool exhausted, clients not getting IP",
    "{device} firewall blocking legitimate traffic to internal portal",
    "{device} temperature warning, fan may have failed",
]

FAULT_PROBABILITY = 0.3
SYSLOG_HOST = "127.0.0.1"
SYSLOG_PORT = 5140
FACILITY = 16


def build_syslog_message(device: str, status: str, message: str) -> str:
    severity = 3 if status == "FAULT" else 6
    pri = FACILITY * 8 + severity
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    msg_body = f"{device}|{status}|{message}"
    return f"<{pri}>1 {timestamp} {device} netmind-sim - - - {msg_body}"


def send_signal(sock):
    device = random.choice(DEVICES)

    if random.random() < FAULT_PROBABILITY:
        scenario = random.choice(FAULT_SCENARIOS).format(device=device)
        syslog_msg = build_syslog_message(device, "FAULT", scenario)
    else:
        syslog_msg = build_syslog_message(device, "OK", "Heartbeat check passed, all systems normal")

    sock.sendto(syslog_msg.encode("utf-8"), (SYSLOG_HOST, SYSLOG_PORT))
    print(f"Sent: {syslog_msg}")


def run_generator(interval_seconds=15, max_logs=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"Syslog sender started. Sending UDP Syslog (RFC 5424) messages to {SYSLOG_HOST}:{SYSLOG_PORT}")
    print(f"Sending every {interval_seconds} seconds. Press Ctrl+C to stop.")

    count = 0
    while max_logs is None or count < max_logs:
        send_signal(sock)
        count += 1
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_generator(interval_seconds=15)