from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT guest_id, count(1) FROM matches WHERE status='active' GROUP BY guest_id")).fetchall()
    print("Active matches per guest:")
    for row in res:
        print(f"Guest: {row[0]}, Count: {row[1]}")
    print("---")
    res2 = db.execute(text("SELECT id, first_name, last_name FROM guests")).fetchall()
    print("All guests:")
    for row in res2:
        print(f"Guest: {row[0]}, Name: {row[1]} {row[2]}")
finally:
    db.close()
