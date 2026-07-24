# NetMind AI — Network Fault Diagnosis Assistant

An AI-powered system that automatically detects, diagnoses, correlates, and reports network faults — ingesting real UDP Syslog events, matching them against a knowledge base using AI embeddings, and generating ready-to-send incident reports with zero manual intervention.

## The Problem
Network engineers spend significant time manually correlating symptoms to root causes and writing incident summaries for management. NetMind AI automates both the diagnostic reasoning and the reporting.

## Architecture
Real UDP Syslog packets (RFC 5424)
↓
Syslog Listener (Python socket, port 5140)
↓
NLP Parser (spaCy + LLM fallback for messy text)
↓
Diagnosis Engine (sentence-embeddings + hybrid scoring + confidence)
↓
Correlation Engine (groups related incidents, 5-min window)
↓
┌────┴────┬──────────────┬─────────────────┐
↓ ↓ ↓ ↓
Database WebSocket Alert Logger Admin Alert
(SQLite) (live push) (email-ready) Generator + PDF


## Features
- **Real network protocol ingestion** — UDP Syslog (RFC 5424), the same protocol Cisco/Juniper devices use
- **AI-based diagnosis** — sentence-transformer embeddings for semantic matching, not just keyword overlap
- **Confidence-aware results** — shows one clear answer when certain, ranked possibilities when ambiguous
- **Incident correlation** — related events grouped as one root issue
- **Engineer feedback loop** — thumbs up/down improves future ranking
- **Auto-escalation** — unresolved Critical incidents get flagged automatically
- **Recurring fault analytics** — live chart of most frequent issues
- **Admin Alert Generator** — auto-drafted root cause / evidence / solution report
- **PDF export**, **network topology visualization**, **JWT authentication**
- **Automated testing** (in-dashboard + CI on GitHub Actions)

## Tech Stack
- **Backend:** FastAPI, SQLAlchemy, SQLite, Python UDP sockets
- **AI/NLP:** spaCy, Sentence-Transformers, Ollama (optional)
- **Frontend:** React (Vite), Recharts, React Flow
- **Auth:** JWT (python-jose, passlib)
- **CI:** GitHub Actions

## Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python run_init_db.py
python seed_data.py
python run_load_kb.py
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment
Copy `backend/.env.example` to `backend/.env` and fill in real values.

## Usage
1. Log in (`admin` / see `.env`)
2. Incidents arrive automatically via the Syslog simulator (`python simulator/log_generator.py`), or submit manually via the dashboard
3. Click any incident for full diagnosis, topology, and Admin Alert generation
4. Download PDF reports, resolve incidents, give feedback

## Testing
- In-dashboard: click "Run End-to-End Tests"
- CI: automatic on every push via GitHub Actions

## Knowledge Base
165 curated network fault scenarios across connectivity, performance, hardware, configuration, wireless, security, and infrastructure categories.

## Future Scope
- Real device integration (point actual Syslog output at the listener)
- Docker containerization
- Real automated email alerting
- Historical trend analysis


