import os
import sys
from datetime import datetime, timezone

# Add backend directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from database.session import SessionLocal
from models.guest import Guest
from models.event import Event
from workers.notifications import dispatch_guest_notification

def run_test():
    db = SessionLocal()
    
    # 1. Setup a test event and guest
    event = db.query(Event).first()
    if not event:
        print("No event found. Please run tests or create one.")
        return

    # Create unconsented guest
    guest = Guest(
        event_id=event.id,
        first_name="Unconsented",
        last_name="Guest",
        phone="+1234567890",
        email="unconsented@example.com",
    )
    db.add(guest)
    db.commit()

    # 2. Test WhatsApp dispatch without consent
    print("Testing WhatsApp without consent...")
    res = dispatch_guest_notification(str(guest.id), channel="meta_whatsapp", force=True)
    print("Result:", res)

    # 3. Add consent and test mock failure
    print("\nTesting WhatsApp with consent (mocking failure)...")
    guest.whatsapp_consent_at = datetime.now(timezone.utc)
    db.commit()

    # Since META_WHATSAPP_TOKEN is not valid, it should fail and fallback
    res2 = dispatch_guest_notification(str(guest.id), channel="meta_whatsapp", force=True)
    print("Result 2:", res2)

    db.delete(guest)
    db.commit()
    db.close()

if __name__ == "__main__":
    run_test()
