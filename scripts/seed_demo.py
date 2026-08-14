#!/usr/bin/env python3
"""
Interactive Demo Data Seeder for Photo Distribution System MVP.

Creates:
- 1 Demo Organizer User (demo@photodistr.com / password123)
- 1 Demo Event ("Grand Gala 2026", selfie_search_enabled=True)
- 1 Demo Guest ("Alice Smith", alice@example.com)
- 3 Real JPEG Sample Photos (Generated with Pillow with visual badges)
- 3 Confirmed Matches & PhotoFace records
- 1 Active Magic Access Code ("DEMOGUEST123")
"""

import sys
import os
import io
import hashlib
import secrets
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from services.storage.local import LocalStorage
from models.user import User
from models.event import Event
from models.guest import Guest
from models.photo import Photo
from models.photo_face import PhotoFace
from models.match import Match
from models.guest_access_token import GuestAccessToken


def create_sample_jpeg(filename_label: str, bg_color: str, text_color: str = "white") -> bytes:
    """Generate a clean 800x600 test JPEG with visual text badge."""
    img = Image.new("RGB", (800, 600), color=bg_color)
    draw = ImageDraw.Draw(img)
    text = f"Demo Photo: {filename_label}"
    
    # Simple rectangle badge
    draw.rectangle([50, 250, 750, 350], fill=(0, 0, 0, 128))
    draw.text((100, 280), text, fill=text_color)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def main():
    print("=" * 60)
    print("      Photo Distribution MVP — Interactive Demo Seeder      ")
    print("=" * 60)

    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    storage = LocalStorage()

    try:
        # 1. Create or get Demo User
        user = db.query(User).filter(User.email == "demo@photodistr.com").first()
        if not user:
            user = User(
                email="demo@photodistr.com",
                password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeg6Lruj3vjPGga31lW",  # "password123"
                name="Demo Host",
            )
            db.add(user)
            db.flush()
            print("[+] Created Demo User: demo@photodistr.com")
        else:
            print("[*] Found existing Demo User: demo@photodistr.com")

        # 2. Create Demo Event
        event = db.query(Event).filter(Event.title == "Grand Gala 2026", Event.created_by == user.id).first()
        if not event:
            event = Event(
                title="Grand Gala 2026",
                description="Annual Celebration & Awards Gala",
                location="Grand Ballroom",
                date=datetime.now(timezone.utc),
                status="active",
                selfie_search_enabled=True,
                created_by=user.id,
            )
            db.add(event)
            db.flush()
            print(f"[+] Created Demo Event: '{event.title}' (ID: {event.id})")
        else:
            print(f"[*] Found existing Demo Event: '{event.title}' (ID: {event.id})")

        # 3. Create Demo Guest
        guest = db.query(Guest).filter(Guest.event_id == event.id, Guest.email == "alice@example.com").first()
        if not guest:
            guest = Guest(
                event_id=event.id,
                first_name="Alice",
                last_name="Smith",
                email="alice@example.com",
                phone="+15551234567",
                embedding_status="success",
            )
            db.add(guest)
            db.flush()
            print(f"[+] Created Demo Guest: {guest.first_name} {guest.last_name}")
        else:
            print(f"[*] Found existing Demo Guest: {guest.first_name} {guest.last_name}")

        # 4. Generate & Save Sample Photos
        photo_colors = [
            ("Photo #1 (Stage Award)", "#1e3a8a"),
            ("Photo #2 (Red Carpet)", "#831843"),
            ("Photo #3 (Dinner Table)", "#065f46"),
        ]

        photos = []
        for label, bg in photo_colors:
            img_bytes = create_sample_jpeg(label, bg)
            key_orig = f"demo/{uuid4().hex}_orig.jpg"
            key_thumb = f"demo/{uuid4().hex}_thumb.jpg"
            key_web = f"demo/{uuid4().hex}_web.jpg"

            storage.put(key_orig, img_bytes)
            storage.put(key_thumb, img_bytes)
            storage.put(key_web, img_bytes)

            photo = Photo(
                event_id=event.id,
                uploaded_by=user.id,
                storage_key=key_orig,
                thumb_key=key_thumb,
                web_key=key_web,
                content_hash=hashlib.sha256(img_bytes).hexdigest(),
                mime_type="image/jpeg",
                file_size=len(img_bytes),
                original_filename=f"{label.lower().replace(' ', '_')}.jpg",
                exif_taken_at=datetime.now(timezone.utc),
            )
            db.add(photo)
            db.flush()

            # Create Face record
            face = PhotoFace(
                photo_id=photo.id,
                event_id=event.id,
                bbox_x=100,
                bbox_y=100,
                bbox_w=200,
                bbox_h=200,
                det_score=0.98,
                quality_score=0.95,
                embedding=[0.1] * 512,
            )
            db.add(face)
            db.flush()

            # Create Match record
            match = Match(
                event_id=event.id,
                photo_id=photo.id,
                guest_id=guest.id,
                photo_face_id=face.id,
                similarity=0.94,
                threshold_used=0.45,
                decision="confirmed",
                status="active",
            )
            db.add(match)
            photos.append(photo)

        print(f"[+] Created & Stored 3 Sample Photos with confirmed matches for Alice.")

        # 5. Create Magic Access Code "DEMOGUEST123"
        access_code = "DEMOGUEST123"
        token_hash = hashlib.sha256(access_code.encode()).hexdigest()

        token_row = db.query(GuestAccessToken).filter(GuestAccessToken.token_hash == token_hash).first()
        if not token_row:
            token_row = GuestAccessToken(
                guest_id=guest.id,
                event_id=event.id,
                token_hash=token_hash,
                token_prefix=access_code[:4],
                expires_at=datetime(2028, 1, 1, tzinfo=timezone.utc),
                created_by=user.id,
            )
            db.add(token_row)
            print(f"[+] Created Magic Link Code: {access_code}")

        db.commit()

        print("\n" + "=" * 60)
        print("                 DEMO DATA SEEDED SUCCESSFULLY!                 ")
        print("=" * 60)
        print(f"Event Title:       {event.title}")
        print(f"Event ID:          {event.id}")
        print(f"Guest Name:        {guest.first_name} {guest.last_name}")
        print(f"Magic Access Code: {access_code}")
        print("-" * 60)
        print("HOW TO TEST THE DEMO:")
        print(f"1. Start Backend Dev Server:   uvicorn main:app --reload --port 8000 (in /backend)")
        print(f"2. Start Frontend Dev Server:  npm run dev (in /frontend)")
        print(f"3. Open Magic Link Guest Portal:")
        print(f"   --> http://localhost:3000/g/{access_code}")
        print(f"4. Open Public Selfie Search:")
        print(f"   --> http://localhost:3000/events/{event.id}/find")
        print(f"5. Test Bulk ZIP Download:")
        print(f"   --> Click 'Download All (3 photos)' inside http://localhost:3000/g/{access_code}")
        print("=" * 60 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[-] Error seeding demo: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    main()
