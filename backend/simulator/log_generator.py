"""
NetMind AI — Syslog Log Generator (simulator)

Sends real RFC 5424 UDP Syslog packets to the backend's syslog_listener.py
(127.0.0.1:5140 by default), in the exact format it expects:

    <PRI>1 TIMESTAMP HOSTNAME APPNAME PROCID MSGID STRUCTURED-DATA MSG

where MSG is:  device|STATUS|message

STATUS is either "OK" (healthy check-in) or a fault status string — the
listener treats anything other than the literal "OK" as a fault.

Usage:
    python log_generator.py                 # run continuously
    python log_generator.py --once           # send a single test fault and exit
    python log_generator.py --interval 15    # change OK check-in interval (seconds)
"""

import argparse
import random
import socket
import time
from datetime import datetime, timezone

HOST = "127.0.0.1"
PORT = 5140

DEVICES = [
    "Core-Switch-01",
    "Router-Branch-01",
    "Router-Branch-02",
    "AP-Floor1",
    "AP-Floor2",
    "Firewall-Main",
    "Server-Room-Switch",
]

# (device, fault message) — message text drives NLP device/category
# extraction and diagnosis matching on the backend, so keep these close
# to real incident phrasing.
FAULT_SCENARIOS = [
    ("Core-Switch-01", "Core switch has no LEDs on and is not responding to ping"),
    ("Router-Branch-01", "Router CPU utilization at 95%, users reporting slow internet"),
    ("AP-Floor1", "Access point on floor 1 keeps disconnecting every few minutes"),
    ("Core-Switch-01", "Port 12 on switch keeps going up and down in the logs"),
    ("Router-Branch-02", "BGP neighbor to ISP router is down"),
    ("Firewall-Main", "Firewall is blocking access to the internal portal"),
    ("Server-Room-Switch", "Port 4 admin shutdown detected, no traffic passing"),
    ("Router-Branch-01", "VPN tunnel to branch office keeps dropping"),
    ("AP-Floor2", "New devices not getting an IP address from DHCP on this AP"),
    ("Core-Switch-01", "Power LED off, switch unreachable, suspected power failure"),
]


def _rfc5424_wrap(msg_body: str, pri: int = 134) -> str:
    """
    Wraps a device|STATUS|message payload in a minimal but structurally
    correct RFC 5424 header so it matches syslog_listener.SYSLOG_PATTERN:
      <PRI>1 TIMESTAMP HOSTNAME APPNAME PROCID MSGID SD MSG
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    hostname = "netmind-sim"
    appname = "netmind"
    procid = "-"
    msgid = "-"
    structured_data = "-"
    return f"<{pri}>1 {timestamp} {hostname} {appname} {procid} {msgid} {structured_data} {msg_body}"


def send_signal(sock: socket.socket, device: str, status: str, message: str):
    payload = f"{device}|{status}|{message}"
    packet = _rfc5424_wrap(payload)
    sock.sendto(packet.encode("utf-8"), (HOST, PORT))
    tag = "OK " if status == "OK" else "FAULT"
    print(f"[generator] sent [{tag}] {device}: {message}")


def send_ok_checkins(sock: socket.socket):
    for device in DEVICES:
        send_signal(sock, device, "OK", "Routine check-in, all systems normal")


def send_random_fault(sock: socket.socket):
    device, message = random.choice(FAULT_SCENARIOS)
    send_signal(sock, device, "FAULT", message)


def run_once(sock: socket.socket):
    """Send a single manual test fault — useful for isolating the signal-flow bug."""
    device, message = FAULT_SCENARIOS[0]
    send_signal(sock, device, "FAULT", message)
    print("[generator] single test packet sent. Check backend logs for "
          "'[syslog_listener] Auto-created incident via Syslog: ...'")


def run_loop(sock: socket.socket, ok_interval: int, fault_interval: int):
    print(f"[generator] streaming to udp://{HOST}:{PORT}")
    print(f"[generator] OK check-ins every {ok_interval}s, faults roughly every {fault_interval}s")
    last_ok = 0
    last_fault = 0
    try:
        while True:
            now = time.time()
            if now - last_ok >= ok_interval:
                send_ok_checkins(sock)
                last_ok = now
            if now - last_fault >= fault_interval:
                send_random_fault(sock)
                last_fault = now
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[generator] stopped.")


def main():
    global HOST, PORT

    parser = argparse.ArgumentParser(description="NetMind AI syslog generator")
    parser.add_argument("--once", action="store_true", help="send a single test fault and exit")
    parser.add_argument("--interval", type=int, default=15, help="OK check-in interval in seconds (default 15)")
    parser.add_argument("--fault-interval", type=int, default=45, help="approx seconds between random faults (default 45)")
    parser.add_argument("--host", default=HOST, help="target host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=PORT, help="target port (default 5140)")
    args = parser.parse_args()

    HOST = args.host
    PORT = args.port

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if args.once:
        run_once(sock)
    else:
        run_loop(sock, args.interval, args.fault_interval)


if __name__ == "__main__":
    main()