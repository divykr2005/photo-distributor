#!/usr/bin/env python3
"""
Backfill script to validate and normalize existing Week 1 reference embeddings.
Asserts:
- Dimension == 512
- Finite float values (no NaN or Inf)
- Applies L2 normalization: v = v / norm(v)
"""
import sys
import os
import json
import numpy as np
from sqlalchemy import create_engine, text

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from core.config import settings

def main():
    database_url = settings.SQLALCHEMY_DATABASE_URI
    engine = create_engine(database_url)

    print("Connecting to database to validate & normalize reference embeddings...")
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT id, guest_id, embedding FROM face_embeddings")).fetchall()
        print(f"Found {len(rows)} reference embeddings.")

        normalized_count = 0
        error_count = 0

        for r in rows:
            emb_id = r.id
            raw_emb = r.embedding

            if isinstance(raw_emb, str):
                vec = np.array(json.loads(raw_emb), dtype=np.float32)
            else:
                vec = np.array(raw_emb, dtype=np.float32)

            if vec.shape[0] != 512:
                print(f"ERROR: Embedding {emb_id} has invalid dimension {vec.shape[0]} (expected 512).")
                error_count += 1
                continue

            if not np.all(np.isfinite(vec)):
                print(f"ERROR: Embedding {emb_id} contains non-finite values (NaN/Inf).")
                error_count += 1
                continue

            norm = np.linalg.norm(vec)
            if norm == 0:
                print(f"ERROR: Embedding {emb_id} has zero norm.")
                error_count += 1
                continue

            if abs(norm - 1.0) > 1e-3:
                vec_norm = (vec / norm).tolist()
                conn.execute(
                    text("UPDATE face_embeddings SET embedding = :emb WHERE id = :id"),
                    {"emb": json.dumps(vec_norm), "id": emb_id}
                )
                normalized_count += 1

        print(f"Normalization complete. Updated {normalized_count} embeddings. Errors encountered: {error_count}.")

if __name__ == "__main__":
    main()
