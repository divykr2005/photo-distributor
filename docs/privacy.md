# Privacy & Data Retention Policy (Week 3)

This document outlines the privacy guarantees, data retention schedules, and metadata protections enforced across the AI Event Photo Distribution platform.

---

## 1. Ephemeral Selfie Processing (Decision D22)

- **No Disk Storage:** Uploaded selfies submitted to `/events/{id}/search-selfie` are processed strictly in RAM. Files are never written to physical disk or object storage.
- **No Face Enrollment:** No `Guests` row, `PhotoFaces` record, or embedding vector is created from a search selfie.
- **No Log Vectors:** Only minimal audit metadata is written to `SelfieSearchLogs`:
  - SHA-256 hashed IP address
  - Event ID
  - Match result count and threshold used (e.g. `0.45`)
  - Execution duration (ms) and timestamp
- **Log Retention Window:** `SelfieSearchLogs` records are automatically purged after **30 days** by the Celery Beat worker (`sweep_expired_zips`).

---

## 2. EXIF & Metadata Stripping

- All `web` (1200px) and `thumb` (400px) photo derivatives generated during ingest undergo complete EXIF metadata stripping.
- **GPS Coordinates Removed:** Latitude, longitude, altitude, camera serial numbers, and device identifiers are stripped prior to public serving.
- **Original File Downloads:** Original image downloads preserve camera settings (ISO, exposure) but sanitize private serial identifiers.

---

## 3. Whitelisted Field Serialization (Decision D30)

No public API endpoint returns sensitive internal fields. The following properties are **strictly excluded** from public responses:
- Floating-point facial embeddings (`embedding` vectors)
- Raw storage keys / filesystem absolute paths
- Guest phone numbers, email addresses, or organizer internal notes
- Face matching similarity scores or threshold margins

---

## 4. Opt-Out & Communication Rules (Decision D28)

- **Opt-Out Flag:** Setting `Guests.notify_opt_out_at` immediately suppresses all automated notification dispatches (SMS/WhatsApp/Email).
- **Opt-Out Check at Dispatch:** Opt-out status is verified at the exact moment of dispatch, preventing queued messages from sending to opted-out guests.
- **Quiet Hours Enforcement:** Notifications generated during 21:00–08:00 (event local time) are automatically rescheduled for 08:00 local time the following morning.
- **Cascade Deletion:** Deleting a guest record permanently cascades and purges associated access tokens, notification logs, and cached ZIP archives.
