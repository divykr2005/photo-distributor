from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT guest_id, count(1), decision FROM matches GROUP BY guest_id, decision")).fetchall()
    print("Matches per guest:")
    for row in res:
        print(f"Guest: {row[0]}, Decision: {row[2]}, Count: {row[1]}")
finally:
    db.close()
