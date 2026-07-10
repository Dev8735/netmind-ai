from sqlalchemy.orm import sessionmaker
from app.models import engine, Incident

Session = sessionmaker(bind=engine)
session = Session()

sample_incidents = [
    Incident(device_type="Switch", incident_description="No ping response, LEDs off",
              category="Connectivity", priority="Critical", symptoms="No ping, LEDs off", status="Open"),
    Incident(device_type="Router", incident_description="High CPU usage causing slow routing",
              category="Performance", priority="High", symptoms="Slow response, high CPU", status="In Progress"),
    Incident(device_type="Access Point", incident_description="Intermittent wifi drops on Floor 3",
              category="Connectivity", priority="Medium", symptoms="Intermittent drops", status="Resolved"),
]

session.add_all(sample_incidents)
session.commit()
print(f"Seeded {len(sample_incidents)} incidents.")