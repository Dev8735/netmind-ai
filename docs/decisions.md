# Tech Stack Decisions

## Backend Framework: FastAPI
Reason: async-native, automatic OpenAPI docs, lighter learning curve
than Django, better performance than Flask for this use case.

## AI/NLP Engine: Ollama (local LLM) + spaCy
Reason: no API key or internet dependency required, fits the
constraint of not connecting to production/external systems,
zero ongoing cost. spaCy handles entity extraction; Ollama
handles reasoning/summarization where rules aren't enough.

## Database: SQLite
Reason: zero-config, file-based, sufficient for POC scale
(100-150 knowledge base records + incident history).

## Frontend: React
Reason: as specified in original blueprint, good fit for
interactive dashboard + forms.

## Decided: July 10/11, 2026 (Day 1)

## Pending
- Ollama model download (llama3) — deferred to Wi-Fi availability,
  needed by Week 2-3 for reasoning layer. Not required for Day 1-9
  work (spaCy rule-based parsing/matching).