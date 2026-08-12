#!/usr/bin/env python3
"""
Seed script to populate database with Week 2 Scale Target:
- 1 Event
- 500 Registered Guests
- 1-3 reference embeddings per guest (~750 total reference vectors)
- 5,000 Event Photos (~25,000 PhotoFaces)
"""
import sys
import os
import uuid
import json
import random
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from core.config import settings

def main():
    print("Starting Week 2 Scale Seeding (500 guests, 5,000 photos, ~25k faces)...")
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

    with engine.begin() as conn:
        # Create test user / organizer
        user_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO users (id, email, password_hash, name, created_at, updated_at)
                VALUES (:id, 'scale_organizer@example.com', 'hashed_pw', 'Scale Test Organizer', NOW(), NOW())
                ON CONFLICT (email) DO UPDATE SET updated_at = NOW()
                RETURNING id;
            """),
            {"id": user_id}
        )
        user_row = conn.execute(text("SELECT id FROM users WHERE email = 'scale_organizer@example.com'")).fetchone()
        user_id = str(user_row.id)

        # Create scale event
        event_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO events (id, title, description, location, date, status, created_by, match_threshold, review_floor, match_margin, created_at, updated_at)
                VALUES (:id, 'Week 2 Scale Benchmark Gala', '5,000 Photo Load Test Event', 'Main Hall', NOW(), 'active', :created_by, 0.42, 0.32, 0.05, NOW(), NOW());
            """),
            {"id": event_id, "created_by": user_id}
        )
        print(f"Created Event ID: {event_id}")

        # Seed 500 guests & reference embeddings
        guest_ids = []
        ref_count = 0
        for g_idx in range(500):
            g_id = str(uuid.uuid4())
            guest_ids.append(g_id)
            conn.execute(
                text("""
                    INSERT INTO guests (id, event_id, first_name, last_name, phone, email, embedding_status, created_at, updated_at)
                    VALUES (:id, :event_id, :fn, :ln, :phone, :email, 'success', NOW(), NOW());
                """),
                {
                    "id": g_id,
                    "event_id": event_id,
                    "fn": f"Guest_{g_idx}",
                    "ln": f"Scale_{g_idx}",
                    "phone": f"+1555000{g_idx:04d}",
                    "email": f"guest_{g_idx}@benchmark.com",
                }
            )

            # 1 to 3 reference embeddings per guest
            num_refs = random.randint(1, 3)
            # Create a base vector for guest
            base_vec = np.random.randn(512).astype(np.float32)
            base_vec /= np.linalg.norm(base_vec)

            for r_idx in range(num_refs):
                ref_id = str(uuid.uuid4())
                noise = np.random.randn(512).astype(np.float32) * 0.05
                ref_vec = base_vec + noise
                ref_vec /= np.linalg.norm(ref_vec)

                conn.execute(
                    text("""
                        INSERT INTO face_embeddings (id, guest_id, embedding, model_version, embedding_dim, quality_score, created_at, updated_at)
                        VALUES (:id, :guest_id, :emb, 'buffalo_l', 512, 0.95, NOW(), NOW());
                    """),
                    {
                        "id": ref_id,
                        "guest_id": g_id,
                        "emb": json.dumps(ref_vec.tolist()),
                    }
                )
                ref_count += 1

        print(f"Seeded 500 Guests with {ref_count} total reference embeddings.")

        # Seed 5,000 photos and ~25,000 PhotoFaces
        batch_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO upload_batches (id, event_id, created_by, total_files, received_files, status, created_at)
                VALUES (:id, :event_id, :created_by, 5000, 5000, 'completed', NOW());
            """),
            {"id": batch_id, "event_id": event_id, "created_by": user_id}
        )

        print("Inserting 5,000 photos and ~25,000 PhotoFaces in bulk chunks...")
        total_faces = 0

        for p_idx in range(5000):
            photo_id = str(uuid.uuid4())
            content_hash = f"hash_{p_idx:05d}_{uuid.uuid4().hex[:8]}"
            faces_in_photo = random.randint(3, 6)

            conn.execute(
                text("""
                    INSERT INTO photos (id, event_id, batch_id, uploaded_by, original_filename, storage_key, web_key, thumb_key, content_hash, mime_type, file_size, width, height, status, face_count, attempts, created_at, updated_at)
                    VALUES (:id, :event_id, :batch_id, :uploaded_by, :filename, :storage_key, :web_key, :thumb_key, :content_hash, 'image/jpeg', 2500000, 1600, 1200, 'processed', :face_count, 1, NOW(), NOW());
                """),
                {
                    "id": photo_id,
                    "event_id": event_id,
                    "batch_id": batch_id,
                    "uploaded_by": user_id,
                    "filename": f"IMG_{p_idx:05d}.jpg",
                    "storage_key": f"events/{event_id}/photos/{photo_id}/original.jpg",
                    "web_key": f"events/{event_id}/photos/{photo_id}/web.jpg",
                    "thumb_key": f"events/{event_id}/photos/{photo_id}/thumb.jpg",
                    "content_hash": content_hash,
                    "face_count": faces_in_photo,
                }
            )

            for f_idx in range(faces_in_photo):
                face_id = str(uuid.uuid4())
                # Pick a target guest to simulate true positive / noise
                target_guest_idx = random.randint(0, 499)
                target_guest_id = guest_ids[target_guest_idx]

                # Fetch base vector logic: Generate embedding with varying similarity
                if random.random() < 0.7:  # 70% genuine matchable face
                    base_vec = np.random.randn(512).astype(np.float32)
                    base_vec /= np.linalg.norm(base_vec)
                    # High similarity float vector
                    vec = base_vec + np.random.randn(512).astype(np.float32) * 0.1
                    is_matchable = True
                    q_flags = None
                else:  # Impostor / low quality face
                    vec = np.random.randn(512).astype(np.float32)
                    is_matchable = random.random() > 0.3
                    q_flags = json.dumps(["blurry"]) if not is_matchable else None

                vec /= np.linalg.norm(vec)

                bx = random.uniform(0.0, 0.8)
                by = random.uniform(0.0, 0.8)
                bw = random.uniform(0.05, 0.15)
                bh = random.uniform(0.05, 0.15)

                conn.execute(
                    text("""
                        INSERT INTO photo_faces (id, photo_id, event_id, bbox_x, bbox_y, bbox_w, bbox_h, det_score, embedding, model_version, embedding_dim, quality_score, is_matchable, quality_flags, crop_key, created_at, updated_at)
                        VALUES (:id, :photo_id, :event_id, :bx, :by, :bw, :bh, 0.92, :emb, 'buffalo_l', 512, 0.88, :is_matchable, :q_flags, :crop_key, NOW(), NOW());
                    """),
                    {
                        "id": face_id,
                        "photo_id": photo_id,
                        "event_id": event_id,
                        "bx": bx,
                        "by": by,
                        "bw": bw,
                        "bh": bh,
                        "emb": json.dumps(vec.tolist()),
                        "is_matchable": is_matchable,
                        "q_flags": q_flags,
                        "crop_key": f"events/{event_id}/photos/{photo_id}/faces/{face_id}.jpg",
                    }
                )
                total_faces += 1

            if (p_idx + 1) % 1000 == 0:
                print(f"Inserted {p_idx + 1} / 5,000 photos ({total_faces} faces)...")

        print(f"Scale Seeding Complete! Total Photos: 5,000 | Total PhotoFaces: {total_faces}")

if __name__ == "__main__":
    main()
