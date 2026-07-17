import random
import time
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "live_logs.txt")

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


def generate_log_line():
    device = random.choice(DEVICES)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if random.random() < FAULT_PROBABILITY:
        scenario = random.choice(FAULT_SCENARIOS).format(device=device)
        return f"[{timestamp}] SIGNAL|FAULT|{device}|{scenario}"
    else:
        return f"[{timestamp}] SIGNAL|OK|{device}|Heartbeat check passed, all systems normal"


def run_generator(interval_seconds=15, max_logs=None):
    print(f"Log generator started. Writing to {LOG_FILE}")
    print(f"Generating a new signal every {interval_seconds} seconds. Press Ctrl+C to stop.")

    count = 0
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        while max_logs is None or count < max_logs:
            line = generate_log_line()
            f.write(line + "\n")
            f.flush()
            print(f"Generated: {line}")
            count += 1
            time.sleep(interval_seconds)


if __name__ == "__main__":
    run_generator(interval_seconds=15)