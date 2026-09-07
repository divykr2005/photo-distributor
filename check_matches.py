from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT decision, status, count(1) FROM matches GROUP BY decision, status")).fetchall()
    for row in res:
        print(f"Decision: {row[0]}, Status: {row[1]}, Count: {row[2]}")
    print("---")
    res2 = db.execute(text("SELECT similarity FROM matches LIMIT 10")).fetchall()
    for row in res2:
        print(f"Sim: {row[0]}")
finally:
    db.close()
