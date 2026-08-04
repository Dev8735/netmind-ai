# NetMind AI — Explainable AI Decision Support System for Network Fault Diagnosis

An AI-powered system that ingests real network events, diagnoses their root cause with
full supporting evidence, explains *why* it reached that conclusion, safely auto-fixes
what it can, and learns from what it gets wrong — instead of handing an engineer a
black-box label.

## The Problem

Network engineers spend significant time manually correlating symptoms to root causes,
verifying candidate explanations, and writing incident summaries for management. Most
"AI troubleshooting" tools make this worse, not better: they output a single confident-
sounding guess with no visibility into how it was reached, so an engineer still has to
independently verify it before trusting it — which defeats the point of automating the
diagnosis in the first place.

NetMind AI is built around the opposite premise: **every diagnosis shows its work.**
Confidence scores, similarity evidence, matched keywords, alternative causes that were
considered and ruled out (with the reason why), and a live decision tree an engineer can
inspect for any fault type — all visible before anyone has to act on it.

## Why Explainable AI, Not a Bigger Model

This project deliberately does not use Random Forest, XGBoost, GNNs, reinforcement
learning, or a full RAG pipeline. All of those require labeled training data at a
production scale that doesn't exist for this problem yet. Instead, NetMind AI combines
sentence-embedding similarity search (grounded, inspectable) with a transparent scoring
and confidence system — every output can be traced back to the specific knowledge-base
entry and evidence that produced it. That traceability is the actual point: a system a
network operations team can audit and trust is more valuable right now than a marginally
more accurate one they can't.

## Architecture

```
Real UDP Syslog packets (RFC 5424)
        │
        ▼
Syslog Listener (Python socket, port 5140)
        │
        ▼
NLP Parser (spaCy + LLM fallback for messy text)
        │
        ▼
Diagnosis Engine (sentence-embeddings + hybrid scoring + confidence)
        │
        ▼
Correlation Engine (groups related incidents, 5-min window)
        │
        ├──────────────┬────────────────┬──────────────────┬─────────────────┐
        ▼               ▼                ▼                   ▼                 ▼
  Auto-Remediation   Admin Alert      PDF Report        Live Dashboard    Scoped AI
  (whitelisted,      Generator        (explainable,      (charts, decision  Conversation
  config-only faults) (Ollama +       full evidence      tree, knowledge   (canned + free-
                       template)       trail)             graph - admin     form Q&A,
                                                           only)             grounded in
                                                                             this incident)
```

Every box downstream of Diagnosis Engine reads the same evidence-bearing diagnosis
object — nothing downstream re-derives or guesses; they all explain the same reasoning
in a different format.

## Features

### Core diagnosis
- Real UDP Syslog ingestion (RFC 5424) — no custom or simulated protocol
- NLP parsing with spaCy, LLM fallback for messy free-text incident reports
- Sentence-embedding similarity search against a 165-entry knowledge base
- Hybrid scoring: embedding similarity + keyword overlap + device/category correlation
- Confidence tiers (high / medium / low) that gate what the system is allowed to do
  automatically

### Explainability (what makes this a decision *support* system, not a black box)
- Every diagnosis shows: similarity score, matched keywords, business impact, and the
  exact verification command and troubleshooting steps for each candidate cause
- **Rejected causes are shown too**, with the specific reason each was ruled out
- **Decision Tree Explorer** (admin panel) — pick any symptom group and see it branch
  into its ranked possible causes with full evidence, or view the diagnosis engine's own
  decision logic as a flowchart
- **Knowledge Graph** (admin panel) — real diagnosed-incident history visualized as
  device ↔ fault-type relationships, weighted by how often each pairing has occurred
- **Explainable PDF reports** — every field visible in the dashboard (confidence,
  evidence, rejected causes, remediation log) is included in the exportable report, not
  just a summary

### Safe automation
- **Auto-remediation** for a whitelisted set of safe, config-only fault types, gated
  strictly on high confidence — the system only acts automatically when it's both
  confident and the fix is known to be low-risk
- **Auto-escalation** — unresolved Critical incidents get flagged automatically
- **Incident correlation** — groups related events within a 5-minute window instead of
  spamming duplicate incidents

### Learning and feedback
- **AI Performance Dashboard** — real accuracy tracked from engineer feedback, broken
  down by confidence tier and trended over time (not a claimed number — a measured one)
- **Learning Mode / Corrections Log** — when an engineer marks a diagnosis unhelpful,
  they specify what the actual cause was; every correction is logged and visible,
  showing exactly where and how the system has been wrong
- **Incident similarity search** — find past incidents that share the same diagnosed
  cause, even when worded completely differently

### Conversational access
- **Scoped AI Conversation** — ask questions about a specific incident (canned buttons
  for common questions, or free-form) and get answers grounded only in that incident's
  actual diagnosis data, with Ollama used opportunistically and a deterministic template
  fallback when it's unavailable

### Operational
- Recurring fault analytics, live severity breakdown, network topology visualization
- Admin Alert Generator (auto-drafted root cause / evidence / solution report)
- Password-gated Admin Panel, separate from the main login, hosting internal
  explainability tooling not needed for day-to-day triage
- JWT authentication, in-dashboard + CI automated testing (GitHub Actions)

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite, Python UDP sockets
- **AI/NLP:** spaCy, Sentence-Transformers (`all-MiniLM-L6-v2`), Ollama (optional,
  `llama3` — every Ollama-dependent feature degrades gracefully to a deterministic
  template when it's unavailable)
- **Frontend:** React 19 (Vite), Recharts, React Flow
- **Auth:** JWT (python-jose, passlib) — two independent gates: main app login and a
  separate Admin Panel password
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
Copy `backend/.env.example` to `backend/.env` and fill in real values. Set
`ADMIN_PANEL_PASSWORD` to control access to the Admin Panel (decision tree, knowledge
graph, diagnosis pipeline view) — separate from the main app's `ADMIN_PASSWORD`.

## Usage

1. Log in (`admin` / see `.env`)
2. Incidents arrive automatically via the Syslog simulator
   (`python simulator/log_generator.py`), or submit manually via the dashboard
3. Click any incident for full diagnosis, evidence, topology, similar past incidents,
   and Ask NetMind AI
4. Download explainable PDF reports, resolve incidents, give feedback (with a
   correction if the diagnosis was wrong)
5. Visit the Admin Panel (separate password) for the decision tree explorer and
   knowledge graph

## Testing

- In-dashboard: click "Run End-to-End Tests"
- CI: automatic on every push via GitHub Actions

## Knowledge Base

165 curated network fault scenarios across connectivity, performance, hardware,
configuration, wireless, security, and infrastructure categories. A subset is tagged
with a `fault_type` for cross-referencing (similarity search, decision tree, knowledge
graph) — expanding this tagging is the most direct way to make those features more
useful going forward.

## Future Scope

- Real device integration (point actual Syslog output at the listener)
- Docker containerization
- Real automated email alerting
- Historical trend analysis
- Broader `fault_type` tagging across the knowledge base
- Expanding the Corrections Log into an active feedback loop that reweights or flags
  KB entries that repeatedly need correcting