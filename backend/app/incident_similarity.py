from sqlalchemy.orm import sessionmaker
from sentence_transformers import util
from .models import engine, Incident
from .diagnosis_engine import model  # reuse the already-loaded embedding model

Session = sessionmaker(bind=engine)

SIMILARITY_THRESHOLD = 0.3
TOP_N = 3


def find_similar_incidents(incident_id: int) -> list:
    """
    Given an incident, finds the top-N most similar *past incidents*
    (not knowledge base entries) using semantic embeddings on the
    incident_description text. Excludes the incident itself.
    Returns a list of dicts with id, device, issue, severity, status,
    and similarity_score - or an empty list if there's nothing to compare
    against or nothing clears the similarity threshold.
    """
    session = Session()
    target = session.query(Incident).filter(Incident.id == incident_id).first()

    if not target:
        session.close()
        return []

    others = session.query(Incident).filter(Incident.id != incident_id).all()
    session.close()

    if not others:
        return []

    target_embedding = model.encode(target.incident_description, convert_to_tensor=True)
    other_texts = [o.incident_description for o in others]
    other_embeddings = model.encode(other_texts, convert_to_tensor=True)

    similarities = util.cos_sim(target_embedding, other_embeddings)[0]

    scored = []
    for idx, incident in enumerate(others):
        score = float(similarities[idx])
        if score > SIMILARITY_THRESHOLD:
            scored.append((score, incident))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_matches = scored[:TOP_N]

    return [
        {
            "id": incident.id,
            "device": incident.device_type,
            "issue": incident.incident_description,
            "severity": incident.priority,
            "status": incident.status,
            "similarity_score": round(score, 3)
        }
        for score, incident in top_matches
    ]