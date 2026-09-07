from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT guest_id, status, decision, count(1) FROM matches WHERE guest_id='308ed55e-2e45-4869-b284-4f5da506f64e' GROUP BY guest_id, status, decision")).fetchall()
    print("Matches for 308ed55e:")
    for row in res:
        print(f"Guest: {row[0]}, Status: {row[1]}, Decision: {row[2]}, Count: {row[3]}")
    print("---")
    res2 = db.execute(text("SELECT similarity, status, decision FROM matches WHERE guest_id='308ed55e-2e45-4869-b284-4f5da506f64e' ORDER BY similarity DESC LIMIT 10")).fetchall()
    print("Top similarities:")
    for row in res2:
        print(f"Sim: {row[0]}, Status: {row[1]}, Decision: {row[2]}")
finally:
    db.close()
