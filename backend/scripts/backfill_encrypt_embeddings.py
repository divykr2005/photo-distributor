import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from services.crypto.providers import get_key_provider
from services.crypto.envelope import (
    generate_key, 
    wrap_key, 
    unwrap_key, 
    encrypt_embedding,
    decrypt_embedding
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_backfill(dry_run: bool = False):
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI) # type: ignore
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        master_key = get_key_provider().unwrap_master_key()
        
        # 1. Backfill Events (Generate KEKs)
        logger.info("Step 1: Backfilling KEKs for Events")
        events_without_kek = db.execute(text("SELECT id FROM events WHERE wrapped_kek IS NULL")).fetchall()
        for row in events_without_kek:
            event_id = row.id
            kek = generate_key()
            wrapped_kek, nonce = wrap_key(kek, master_key)
            # Prepend nonce to wrapped_kek for storage or store separately. 
            # In envelope.py we assumed we pass them. We should concatenate nonce + ciphertext for ease, 
            # or we need to add nonce columns for KEKs and DEKs too.
            # Wait, the models for Event and Guest ONLY have `wrapped_kek` and `wrapped_dek`. 
            # We must prepend the 12-byte nonce to the wrapped key.
            kek_blob = nonce + wrapped_kek
            
            if not dry_run:
                db.execute(text("UPDATE events SET wrapped_kek = :kek, kek_key_id = 'local' WHERE id = :id"),
                           {"kek": kek_blob, "id": event_id})
        
        if not dry_run:
            db.commit()
            
        logger.info(f"Processed {len(events_without_kek)} events.")
        
        # 2. Backfill Guests (Generate DEKs)
        logger.info("Step 2: Backfilling DEKs for Guests")
        guests_without_dek = db.execute(text("""
            SELECT g.id, e.wrapped_kek 
            FROM guests g 
            JOIN events e ON g.event_id = e.id 
            WHERE g.wrapped_dek IS NULL
        """)).fetchall()
        
        for row in guests_without_dek:
            guest_id = row.id
            kek_blob = row.wrapped_kek
            if not kek_blob:
                logger.error(f"Guest {guest_id} belongs to an event without a KEK. Skipping.")
                continue
                
            kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
            kek = unwrap_key(kek_wrapped, kek_nonce, master_key)
            
            dek = generate_key()
            wrapped_dek, dek_nonce = wrap_key(dek, kek)
            dek_blob = dek_nonce + wrapped_dek
            
            if not dry_run:
                db.execute(text("UPDATE guests SET wrapped_dek = :dek, dek_key_id = 'local' WHERE id = :id"),
                           {"dek": dek_blob, "id": guest_id})
        
        if not dry_run:
            db.commit()
            
        logger.info(f"Processed {len(guests_without_dek)} guests.")
        
        # 3. Encrypt FaceEmbeddings
        logger.info("Step 3: Encrypting FaceEmbeddings")
        embeddings = db.execute(text("""
            SELECT fe.id, fe.embedding, fe.model_version, fe.guest_id, g.wrapped_dek, g.event_id
            FROM face_embeddings fe
            JOIN guests g ON fe.guest_id = g.id
            WHERE fe.embedding_enc IS NULL AND fe.embedding IS NOT NULL
        """)).fetchall()
        
        success_count = 0
        
        for row in embeddings:
            fe_id = row.id
            guest_id = row.guest_id
            event_id = row.event_id
            model_version = row.model_version
            plaintext_embedding_str = row.embedding # This is vector(512) typically returned as a string in pg8000/psycopg
            dek_blob = row.wrapped_dek
            
            if not dek_blob:
                logger.error(f"FaceEmbedding {fe_id} belongs to a guest without a DEK. Skipping.")
                continue
                
            # Need KEK to unwrap DEK
            event_row = db.execute(text("SELECT wrapped_kek FROM events WHERE id = :id"), {"id": event_id}).fetchone()
            kek_blob = event_row.wrapped_kek # type: ignore
            kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
            kek = unwrap_key(kek_wrapped, kek_nonce, master_key)
            
            dek_nonce, dek_wrapped = dek_blob[:12], dek_blob[12:]
            dek = unwrap_key(dek_wrapped, dek_nonce, kek)
            
            # Convert embedding to bytes
            if isinstance(plaintext_embedding_str, str):
                embedding_bytes = plaintext_embedding_str.encode('utf-8')
            else:
                embedding_bytes = str(plaintext_embedding_str).encode('utf-8')
                
            ciphertext, nonce = encrypt_embedding(
                embedding_bytes, dek, str(guest_id), str(event_id), str(fe_id), model_version
            )
            
            # Verification round-trip before committing
            decrypted_bytes = decrypt_embedding(
                ciphertext, nonce, dek, str(guest_id), str(event_id), str(fe_id), model_version
            )
            
            assert decrypted_bytes == embedding_bytes, f"Round-trip failed for embedding {fe_id}!"
            
            if not dry_run:
                db.execute(text("""
                    UPDATE face_embeddings 
                    SET embedding_enc = :enc, enc_nonce = :nonce, enc_key_id = 'local' 
                    WHERE id = :id
                """), {"enc": ciphertext, "nonce": nonce, "id": fe_id})
                
            success_count += 1
            
        if not dry_run:
            db.commit()
            
        logger.info(f"Successfully processed {success_count} face embeddings.")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Backfill failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run without committing")
    args = parser.parse_args()
    
    run_backfill(dry_run=args.dry_run)
