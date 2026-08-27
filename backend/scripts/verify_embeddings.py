import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from services.crypto.providers import get_key_provider
from services.crypto.envelope import unwrap_key, decrypt_embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_encrypted_embeddings():
    """
    Verifies that all encrypted embeddings can be decrypted successfully
    and they match the plaintext if available.
    """
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI) # type: ignore
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        master_key = get_key_provider().unwrap_master_key()
        
        embeddings = db.execute(text("""
            SELECT fe.id, fe.embedding, fe.embedding_enc, fe.enc_nonce, 
                   fe.model_version, fe.guest_id, g.wrapped_dek, g.event_id,
                   e.wrapped_kek
            FROM face_embeddings fe
            JOIN guests g ON fe.guest_id = g.id
            JOIN events e ON g.event_id = e.id
            WHERE fe.embedding_enc IS NOT NULL
        """)).fetchall()
        
        if not embeddings:
            logger.info("No encrypted embeddings found.")
            return
            
        success_count = 0
        error_count = 0
        
        for row in embeddings:
            try:
                kek_blob = row.wrapped_kek
                kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
                kek = unwrap_key(kek_wrapped, kek_nonce, master_key)
                
                dek_blob = row.wrapped_dek
                dek_nonce, dek_wrapped = dek_blob[:12], dek_blob[12:]
                dek = unwrap_key(dek_wrapped, dek_nonce, kek)
                
                decrypted = decrypt_embedding(
                    ciphertext=row.embedding_enc,
                    nonce=row.enc_nonce,
                    dek=dek,
                    guest_id=str(row.guest_id),
                    event_id=str(row.event_id),
                    face_embedding_id=str(row.id),
                    model_version=row.model_version
                )
                
                if row.embedding:
                    # Compare if we still have plaintext
                    pt = row.embedding if isinstance(row.embedding, str) else str(row.embedding)
                    assert decrypted.decode('utf-8') == pt, "Mismatch with plaintext!"
                    
                success_count += 1
            except Exception as e:
                logger.error(f"Verification failed for FaceEmbedding {row.id}: {e}")
                error_count += 1
                
        logger.info(f"Verified {success_count} embeddings successfully. Errors: {error_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_encrypted_embeddings()
