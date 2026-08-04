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

Each message follows the RFC 5424 structured format:

```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [STRUCTURED-DATA] MSG
```

Example, as actually sent by the simulator:

```
<134>1 2026-07-28T05:03:11.482Z Server-Room-Switch NetMind-Agent 1024 ID47 - Port 4 admin shutdown detected, no traffic passing
```

Breaking that down:
- `<134>` — PRI (priority): facility 16 (local0) × 8 + severity 6 (informational)
- `1` — VERSION (RFC 5424)
- `2026-07-28T05:03:11.482Z` — TIMESTAMP, ISO 8601 with milliseconds, UTC
- `Server-Room-Switch` — HOSTNAME, the reporting device
- `NetMind-Agent` — APP-NAME, the simulated agent process
- `1024` — PROCID
- `ID47` — MSGID
- `-` — STRUCTURED-DATA (unused, per spec this is the "nil" value)
- Everything after the last `-` is the free-text MSG body — this is what
  the NLP parser and diagnosis engine actually process

The listener extracts HOSTNAME (mapped to `device`) and the MSG body (mapped to
`incident_description`) and hands them to the same NLP parsing and diagnosis pipeline
used for manually-submitted incidents — there is no separate code path for
Syslog-sourced vs. manually-entered incidents.

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