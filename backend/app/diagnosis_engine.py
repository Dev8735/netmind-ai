from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from sentence_transformers import SentenceTransformer, util
from .models import engine, KnowledgeBase, Feedback, Incident

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


def get_matched_keywords(incident_keywords: list, kb_entry) -> list:
    kb_text = f"{kb_entry.incident_description} {kb_entry.symptoms}".lower()
    return [kw for kw in incident_keywords if kw.lower() in kb_text]


def get_cause_penalty(cause_text: str) -> float:
    """
    Returns a small penalty (0 to -0.15) for causes that have received
    negative feedback historically, so they rank slightly lower next time.
    """
    session = Session()
    try:
        negative_count = session.query(func.count(Feedback.id)).join(
            Incident, Feedback.incident_id == Incident.id
        ).filter(
            Feedback.helpful == "no",
            Incident.diagnosis_json.like(f'%{cause_text[:30]}%')
        ).scalar()

        return -min((negative_count or 0) * 0.03, 0.15)
    except Exception:
        return 0.0
    finally:
        session.close()


def diagnose_incident(device: str, category: str, keywords: list, raw_text: str = None) -> dict:
    if _kb_cache["entries"] is None:
        _load_kb_cache()

    kb_entries = _kb_cache["entries"]
    kb_embeddings = _kb_cache["embeddings"]

    if not kb_entries or kb_embeddings is None:
        return {"matched": False, "severity": "Medium", "causes": [], "confidence": "low", "confidence_score": 0.0}

    incident_text = raw_text if raw_text else " ".join(keywords)
    incident_embedding = model.encode(incident_text, convert_to_tensor=True)

    similarities = util.cos_sim(incident_embedding, kb_embeddings)[0]

    scored_matches = []
    for idx, entry in enumerate(kb_entries):
        embedding_score = float(similarities[idx])
        keyword_score = calculate_keyword_score(keywords, entry)
        device_boost = 0.15 if device.lower() in entry.incident_description.lower() else 0
        category_boost = 0.1 if category.lower() in entry.symptoms.lower() or category.lower() in entry.incident_description.lower() else 0
        penalty = get_cause_penalty(entry.possible_cause)

        combined_score = embedding_score + (keyword_score * 0.05) + device_boost + category_boost + penalty
        scored_matches.append((combined_score, embedding_score, entry))

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    top_matches = [m for m in scored_matches[:3] if m[0] > 0.25]

    if not top_matches:
        return {"matched": False, "severity": "Medium", "causes": [], "confidence": "low", "confidence_score": 0.0}

    causes = []
    for combined_score, embedding_score, entry in top_matches:
        matched_kw = get_matched_keywords(keywords, entry)
        causes.append({
            "cause": entry.possible_cause,
            "probability": entry.probability,
            "verification_command": entry.verification_command,
            "troubleshooting_steps": entry.troubleshooting_steps,
            "match_score": round(combined_score, 3),
            "similarity_score": round(embedding_score, 3),
            "matched_keywords": matched_kw,
            "fault_type": entry.fault_type or ""
        })

    top_severity = top_matches[0][2].severity
    top_score = top_matches[0][0]

    if top_score > 0.9:
        confidence = "high"
    elif top_score > 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "matched": True,
        "severity": top_severity,
        "causes": causes,
        "confidence": confidence,
        "confidence_score": round(top_score, 3)
    }