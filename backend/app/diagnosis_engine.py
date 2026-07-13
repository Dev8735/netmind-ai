from sqlalchemy.orm import sessionmaker
from .models import engine, KnowledgeBase

Session = sessionmaker(bind=engine)


def calculate_match_score(incident_keywords: list, kb_entry) -> int:
    """Count how many incident keywords appear in this KB entry's text fields."""
    kb_text = f"{kb_entry.incident_description} {kb_entry.symptoms}".lower()
    score = 0
    for kw in incident_keywords:
        if kw.lower() in kb_text:
            score += 1
    return score


def diagnose_incident(device: str, category: str, keywords: list) -> dict:
    session = Session()
    kb_entries = session.query(KnowledgeBase).all()

    scored_matches = []
    for entry in kb_entries:
        score = calculate_match_score(keywords, entry)
        # Small boost if device name appears in the KB description too
        if device.lower() in entry.incident_description.lower():
            score += 2
        if score > 0:
            scored_matches.append((score, entry))

    session.close()

    if not scored_matches:
        return {
            "matched": False,
            "severity": "Medium",
            "causes": []
        }

    scored_matches.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored_matches[:3]

    causes = []
    for score, entry in top_matches:
        causes.append({
            "cause": entry.possible_cause,
            "probability": entry.probability,
            "verification_command": entry.verification_command,
            "troubleshooting_steps": entry.troubleshooting_steps,
            "match_score": score
        })

    # Take severity from the single best match
    top_severity = top_matches[0][1].severity

    return {
        "matched": True,
        "severity": top_severity,
        "causes": causes
    }