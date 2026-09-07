from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT id FROM events LIMIT 1")).fetchone()
    print(f"Event ID: {res[0]}")
    from workers.matching import run_event_match
    run_event_match.delay(str(res[0]))
    print(f"Triggered match for {res[0]}")
finally:
    db.close()
