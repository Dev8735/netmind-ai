# Network Protocol: UDP Syslog (RFC 5424)

NetMind AI ingests network events via UDP Syslog, the industry-standard
protocol used by real network devices (Cisco, Juniper, etc.) for event
reporting — rather than a custom or simulated text format.

## Implementation

**Listener** (`backend/app/syslog_listener.py`)
- UDP socket bound to `127.0.0.1:5140`
- Port 5140 is used instead of the standard port 514 because binding to
  any port below 1024 requires administrator/root privileges on most
  operating systems, including Windows. In a production deployment this
  would run on 514 with appropriate permissions, or behind a privileged
  proxy/forwarder.
- Runs as a background thread inside the FastAPI application, started on
  server startup

**Sender** (`backend/simulator/log_generator.py`)
- Simulates monitored network devices reporting their status
- Builds properly formatted RFC 5424 Syslog messages and sends them over
  UDP using Python's `socket` module

## Message Format

## Why Syslog Over SNMP

Syslog was chosen over SNMP traps for two reasons:
1. It matches the free-text, human-readable event style that NetMind AI's
   NLP pipeline (spaCy + sentence embeddings) is designed to parse
2. It requires no MIB definitions or binary encoding — a closer real-world
   match to how the system already processes incident text, and simpler
   to implement without sacrificing authenticity

## Path to Production

To connect this system to real network hardware, no architecture change
is required — actual devices would be configured to send their Syslog
output to the listener's address and port (514 in production), and the
existing pipeline would process real events exactly as it processes the
simulator's events today.