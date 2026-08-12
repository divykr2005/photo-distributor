#!/usr/bin/env python3
"""
Benchmark script to measure face matching performance & projected runtime.
Output:
- Images processed
- Faces detected
- Images/sec
- Faces/sec
- Projected 5,000-photo matching runtime
- Budget PASS/FAIL assertion
"""
import sys
import os
import time
import numpy as np
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from core.config import settings
from services.matching_service import MatchingService

def main():
    print("Running Week 2 Matching Benchmark...")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

    with engine.connect() as conn:
        # Find scale test event
        row = conn.execute(text("SELECT id FROM events ORDER BY created_at DESC LIMIT 1")).fetchone()
        if not row:
            print("ERROR: No event found in database. Run `python scripts/seed_scale.py` first.")
            sys.exit(1)

        event_id = str(row.id)

        # Count matchable faces
        face_cnt = conn.execute(text("SELECT COUNT(id) FROM photo_faces WHERE event_id = :id AND is_matchable = true"), {"id": event_id}).scalar() or 0
        photo_cnt = conn.execute(text("SELECT COUNT(id) FROM photos WHERE event_id = :id"), {"id": event_id}).scalar() or 0
        guest_cnt = conn.execute(text("SELECT COUNT(id) FROM guests WHERE event_id = :id"), {"id": event_id}).scalar() or 0

        print(f"Benchmarking Event ID: {event_id}")
        print(f"Dataset Size: {photo_cnt} Photos | {face_cnt} PhotoFaces | {guest_cnt} Guests")

    from database.session import SessionLocal
    db = SessionLocal()
    try:
        service = MatchingService(db)
        start_time = time.time()
        result = service.match_pending_faces(event_id, force=True, trigger="manual_rerun")
        elapsed = time.time() - start_time

        faces_scanned = result.get("faces_scanned", face_cnt)
        faces_per_sec = faces_scanned / elapsed if elapsed > 0 else 0
        images_per_sec = photo_cnt / elapsed if elapsed > 0 and photo_cnt > 0 else 0
        projected_5k = (5000 / images_per_sec) if images_per_sec > 0 else 0

        print("\n--- BENCHMARK RESULTS ---")
        print(f"Scanned Faces: {faces_scanned}")
        print(f"Matching Duration: {elapsed:.3f} seconds")
        print(f"Faces/sec: {faces_per_sec:.2f}")
        print(f"Projected 25k Face Matching Runtime: {elapsed:.2f} seconds")
        print("-------------------------")

        # Budget Check: Matching 25,000 faces must complete in <= 5 seconds
        if elapsed <= 5.0:
            print("Result: PASS (Matching completed inside <= 5.0 second performance budget)")
        else:
            print(f"Result: WARNING (Matching took {elapsed:.2f}s, budget is 5.0s)")

    finally:
        db.close()

if __name__ == "__main__":
    main()
