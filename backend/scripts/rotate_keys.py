import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from services.crypto.providers import get_key_provider
from services.crypto.envelope import wrap_key, unwrap_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rotate_master_key(old_master_key_hex: str, new_master_key_hex: str, dry_run: bool = False):
    """
    Rotates the master key by unwrapping all KEKs with the old master key 
    and re-wrapping them with the new master key.
    """
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI) # type: ignore
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    old_master_key = bytes.fromhex(old_master_key_hex)
    new_master_key = bytes.fromhex(new_master_key_hex)
    
    try:
        events = db.execute(text("SELECT id, wrapped_kek FROM events WHERE wrapped_kek IS NOT NULL")).fetchall()
        success_count = 0
        
        for row in events:
            event_id = row.id
            kek_blob = row.wrapped_kek
            
            kek_nonce, kek_wrapped = kek_blob[:12], kek_blob[12:]
            
            try:
                # Unwrap with old key
                kek = unwrap_key(kek_wrapped, kek_nonce, old_master_key)
            except Exception as e:
                logger.error(f"Failed to unwrap KEK for event {event_id} using old master key. Already rotated? {e}")
                continue
            
            # Wrap with new key
            new_wrapped_kek, new_nonce = wrap_key(kek, new_master_key)
            new_kek_blob = new_nonce + new_wrapped_kek
            
            if not dry_run:
                db.execute(
                    text("UPDATE events SET wrapped_kek = :kek WHERE id = :id"),
                    {"kek": new_kek_blob, "id": event_id}
                )
                
            success_count += 1
            
        if not dry_run:
            db.commit()
            logger.info(f"Successfully rotated master key for {success_count} events.")
        else:
            logger.info(f"Dry-run: Would have rotated master key for {success_count} events.")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to rotate keys: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate master key")
    parser.add_argument("--old-key", required=True, help="Old master key in hex (64 chars)")
    parser.add_argument("--new-key", required=True, help="New master key in hex (64 chars)")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing")
    
    args = parser.parse_args()
    
    if len(args.old_key) != 64 or len(args.new_key) != 64:
        logger.error("Master keys must be 64 hexadecimal characters.")
        sys.exit(1)
        
    rotate_master_key(args.old_key, args.new_key, args.dry_run)
