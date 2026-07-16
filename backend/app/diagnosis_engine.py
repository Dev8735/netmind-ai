from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer, util
from .models import engine, KnowledgeBase

Session = sessionmaker(bind=engine)

print("Loading embedding model (first run may take a moment)...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model loaded.")

_kb_cache = {"entries": None, "embeddings": None}


def _load_kb_cache():
    session = Session()
    entries = session.query(KnowledgeBase).all()
    session.close()

    if not entries:
        _kb_cache["entries"] = []
        _kb_cache["embeddings"] = None
        return

    kb_texts = [f"{e.incident_description} {e.symptoms}" for e in entries]
    print(f"Embedding {len(kb_texts)} knowledge base entries...")
    embeddings = model.encode(kb_texts, convert_to_tensor=True)
    print("Knowledge base embeddings cached.")

    _kb_cache["entries"] = entries
    _kb_cache["embeddings"] = embeddings


def refresh_kb_cache():
    """Call this after knowledge base changes (e.g. reloading CSV)."""
    _load_kb_cache()


def calculate_keyword_score(incident_keywords: list, kb_entry) -> int:
    kb_text = f"{kb_entry.incident_description} {kb_entry.symptoms}".lower()
    score = 0
    for kw in incident_keywords:
        if kw.lower() in kb_text:
            score += 1
    return score


def diagnose_incident(device: str, category: str, keywords: list, raw_text: str = None) -> dict:
    if _kb_cache["entries"] is None:
        _load_kb_cache()

    kb_entries = _kb_cache["entries"]
    kb_embeddings = _kb_cache["embeddings"]

    if not kb_entries or kb_embeddings is None:
        return {"matched": False, "severity": "Medium", "causes": []}

    incident_text = raw_text if raw_text else " ".join(keywords)
    incident_embedding = model.encode(incident_text, convert_to_tensor=True)

    similarities = util.cos_sim(incident_embedding, kb_embeddings)[0]

    scored_matches = []
    for idx, entry in enumerate(kb_entries):
        embedding_score = float(similarities[idx])
        keyword_score = calculate_keyword_score(keywords, entry)
        device_boost = 0.15 if device.lower() in entry.incident_description.lower() else 0

        combined_score = embedding_score + (keyword_score * 0.05) + device_boost
        scored_matches.append((combined_score, entry))

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    top_matches = [m for m in scored_matches[:3] if m[0] > 0.25]

    if not top_matches:
        return {"matched": False, "severity": "Medium", "causes": []}

    causes = []
    for score, entry in top_matches:
        causes.append({
            "cause": entry.possible_cause,
            "probability": entry.probability,
            "verification_command": entry.verification_command,
            "troubleshooting_steps": entry.troubleshooting_steps,
            "match_score": round(score, 3),
            "fault_type": entry.fault_type or ""
        })

    top_severity = top_matches[0][1].severity

    return {
        "matched": True,
        "severity": top_severity,
        "causes": causes
    }