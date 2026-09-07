from database.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    res = db.execute(text("SELECT count(1) FROM photo_faces")).scalar()
    print(f"Total photo faces: {res}")
    res2 = db.execute(text("SELECT count(1) FROM face_embeddings")).scalar()
    print(f"Total guest embeddings: {res2}")
    res3 = db.execute(text("SELECT guest_id, count(1) FROM face_embeddings GROUP BY guest_id")).fetchall()
    print("Embeddings per guest:")
    for row in res3:
        print(f"Guest: {row[0]}, Count: {row[1]}")
finally:
    db.close()
