from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from .models import engine, Incident

Session = sessionmaker(bind=engine)

CORRELATION_WINDOW_MINUTES = 5


def find_correlated_parent(device: str, category: str, exclude_id: int = None) -> int:
    """
    Looks for a recent incident with the same device+category within the
    correlation window. Returns its id (as parent) if found, else None.
    """
    session = Session()
    cutoff = datetime.utcnow() - timedelta(minutes=CORRELATION_WINDOW_MINUTES)

    query = session.query(Incident).filter(
        Incident.device_type == device,
        Incident.category == category,
        Incident.created_at >= cutoff
    )
    if exclude_id:
        query = query.filter(Incident.id != exclude_id)

    existing = query.order_by(Incident.created_at.asc()).first()
    session.close()

    if not existing:
        return None

    return existing.parent_incident_id if existing.parent_incident_id else existing.id