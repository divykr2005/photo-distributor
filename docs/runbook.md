# Operations Runbook (Week 3)

This operational guide provides procedures for administrative tasks, incident response, and system recovery.

---

## 1. Revoking or Rotating a Leaked Magic Link

If a magic link access code is accidentally shared publicly or compromised:

### Revoke Token
```bash
python -c "
from database.session import SessionLocal
from models.guest_access_token import GuestAccessToken
from datetime import datetime, timezone

db = SessionLocal()
token = db.query(GuestAccessToken).filter(GuestAccessToken.token_prefix == 'PREFIX').first()
if token:
    token.revoked_at = datetime.now(timezone.utc)
    db.commit()
    print('Token revoked')
"
```

### Rotate Token (Generate New Link)
Navigate to Organizer Dashboard → Event Guests → Select Guest → Click **"Rotate Magic Link"**. This revokes the previous token and issues a fresh 22-character access code.

---

## 2. Re-Notifying Guests

To manually trigger notification dispatch for guests who have not received their link:

```bash
# Trigger notification dispatch for event
python -c "
from workers.notifications import dispatch_event_notifications
dispatch_event_notifications.delay('EVENT_UUID')
"
```

---

## 3. Clearing Stuck or Corrupted ZIP Archives

If a background ZIP build task gets stuck in `processing` status due to a worker restart:

```bash
python -c "
from database.session import SessionLocal
from models.zip_archive import ZipArchive, ZipStatus

db = SessionLocal()
stuck = db.query(ZipArchive).filter(ZipArchive.status == ZipStatus.PROCESSING.value).all()
for z in stuck:
    z.status = ZipStatus.FAILED.value
    z.error_message = 'Interrupted by worker restart'
db.commit()
print(f'Cleared {len(stuck)} stuck archives')
"
```

---

## 4. Disk Watermark Alert (Storage Above 80%)

If the storage volume exceeds 80% usage, `/guest/{token}/zip` endpoints return `503 Service Unavailable`.

### Emergency Cleanup Steps:
1. Run the expired ZIP sweeper manually:
   ```bash
   python -c "
   from workers.zip_worker import sweep_expired_zips
   sweep_expired_zips()
   "
   ```
2. Verify available disk space:
   ```bash
   df -h
   ```
3. If necessary, adjust `ZIP_TTL_HOURS` or purge older temporary files in `uploads/zips/`.
