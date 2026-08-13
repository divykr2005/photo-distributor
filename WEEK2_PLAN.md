# WEEK 2 BUILD PROMPT

## AI Event Photo Distribution Platform

### Phase 2 — Photo Ingestion → Face Extraction → Matching → Organizer Gallery

---

# 1. YOUR ROLE

You are the primary senior software engineer implementing **Week 2** of an existing AI-powered event photo platform.

You are working inside an existing Week 1 codebase.

Your job is to implement the Week 2 photo-processing and face-matching pipeline **completely**, not as a prototype.

Do not redesign the architecture unnecessarily.

Do not introduce technologies that are not specified here.

Do not implement Week 3 or Week 4 features.

If a decision is explicitly locked below, follow it exactly.

If something is not specified and the choice could affect architecture, data correctness, security, performance, or future compatibility:

**STOP AND FLAG THE DECISION. DO NOT GUESS.**

---

# 2. EXISTING PRODUCT

The product is an AI event photography platform.

The workflow is:

1. Organizer creates an event.
2. Guests register for the event.
3. Each guest provides a reference face image.
4. Week 1 generates a quality-checked 512-dimensional face embedding.
5. Photographer uploads thousands of event photos.
6. Week 2 detects faces inside those photos.
7. Each detected face receives a 512-dimensional embedding.
8. The system compares photo faces against registered guests.
9. Each photo face becomes:

   * auto-confirmed
   * review
   * rejected
10. Organizer can inspect photos, guest galleries, and uncertain matches.
11. Week 3 will later handle guest-facing delivery.

Week 2 therefore owns:

**PHOTO UPLOAD → PHOTO PROCESSING → FACE EXTRACTION → EMBEDDING → MATCHING → ORGANIZER GALLERY/REVIEW**

Week 2 does NOT own guest delivery.

---

# 3. WEEK 1 ASSUMPTIONS

Assume Week 1 provides:

* FastAPI backend
* Next.js frontend
* PostgreSQL
* pgvector
* SQLAlchemy
* Alembic
* JWT authentication
* Organizer/event ownership checks
* Guests
* Guest reference images
* FaceEmbeddings
* InsightFace
* 512-dimensional reference embeddings

Week 1 reference embeddings may contain multiple embeddings for the same guest.

This is intentional.

A guest can therefore have:

```text
Guest A
 ├── reference embedding 1
 ├── reference embedding 2
 └── reference embedding 3
```

Do NOT assume one embedding per guest.

Week 1's face embedding storage is one-to-many by design.

---

# 4. SCALE TARGET — LOCKED

The system must be designed and tested for:

```text
1 event
500 registered guests
5,000 uploaded photos
~4 faces/photo
~20,000–30,000 PhotoFaces
target approximately 25,000 faces
```

This is the Week 2 scale target.

Do not optimize for millions of photos.

Do not create an architecture that fails at 5,000 photos.

Do not create an architecture unnecessarily designed for 5 million photos.

The entire matching workload is approximately:

```text
25,000 photo faces
×
500 guests
×
512 dimensions
```

25,000 × 512 float32 is approximately 51 MB.

The guest reference matrix is approximately 1 MB.

Therefore:

**The matching operation itself is not the bottleneck.**

Face detection and image processing are the expensive stages.

Architect accordingly.

The original specification explicitly sets this 500-guest/5,000-photo target and performance budget.

---

# 5. WEEK 2 DEFINITION OF DONE

Week 2 is complete only when all of the following are true:

* [ ] Photographer can upload 5,000 photos.
* [ ] Uploads use bounded concurrency.
* [ ] Uploading never loads all files into server RAM.
* [ ] Individual uploads can fail without killing the batch.
* [ ] Individual files can be retried.
* [ ] Exact duplicate files are detected using SHA-256.
* [ ] Duplicate uploads do not create another Photo row.
* [ ] Celery + Redis process photos asynchronously.
* [ ] Worker crashes do not create duplicate PhotoFaces.
* [ ] Redis restarts do not corrupt processing.
* [ ] Every detected face gets a PhotoFaces row.
* [ ] Every matchable face receives a normalized 512-dim embedding.
* [ ] Low-quality faces remain stored but are excluded from matching.
* [ ] Face bounding boxes are normalized to `[0,1]`.
* [ ] Face crops are persisted.
* [ ] Matching uses exact NumPy matrix multiplication at this scale.
* [ ] Matching supports multiple reference embeddings per guest.
* [ ] Guest score is the maximum similarity across that guest's reference embeddings.
* [ ] Top-2 comparison uses two distinct guests.
* [ ] Matching is batched, not one match run per uploaded photo.
* [ ] A new guest can be matched against existing event photo faces.
* [ ] Manual organizer decisions survive matching re-runs.
* [ ] Organizer can inspect event photos.
* [ ] Organizer can inspect a guest's matched photos.
* [ ] Organizer can review uncertain matches.
* [ ] Organizer can confirm/reject/manual-assign matches.
* [ ] Photo deletion cascades correctly.
* [ ] Guest deletion removes matches but leaves photo faces.
* [ ] Media endpoints enforce organizer/event ownership.
* [ ] Embeddings never appear in API responses.
* [ ] Calibration is documented.
* [ ] 500 guests + 5,000 photos can complete inside the performance budget.
* [ ] Fresh `docker-compose up` starts the complete Week 2 stack.

---

# 6. EXPLICITLY OUT OF SCOPE

DO NOT BUILD:

* WhatsApp
* Twilio
* SMS
* public guest galleries
* public gallery links
* ZIP downloads
* guest notifications
* perceptual image deduplication
* blur-based "best photo" selection
* smile scoring
* analytics platform
* cloud/S3 storage
* payments
* multi-organizer architecture
* search-by-selfie
* encrypted embeddings
* production cloud deployment

Exact-byte SHA-256 deduplication IS in scope.

Perceptual deduplication is NOT.

The source plan explicitly separates Week 2 from Week 3 delivery and Week 4 quality/scale work.

---

# 7. TECH STACK — LOCKED

Use:

```text
Frontend:
Next.js
React
TypeScript
Tailwind CSS
Axios
@tanstack/react-virtual

Backend:
FastAPI
Python
SQLAlchemy
Alembic
Pydantic

Database:
PostgreSQL
pgvector

AI:
InsightFace
buffalo_l
OpenCV
Pillow
pillow-heif

Workers:
Celery
Redis
Celery Beat

Storage:
Local filesystem through StorageBackend abstraction

Container:
Docker
docker-compose

Matching:
NumPy
pgvector for ad-hoc lookup only
```

Do not replace Celery with another queue.

Do not replace Redis.

Do not replace InsightFace.

Do not introduce Kafka, RabbitMQ, Kubernetes, S3, etc.

---

# 8. CRITICAL ARCHITECTURE RULE

The architecture must look approximately like:

```text
Browser
   |
   | 1 file/request
   v
FastAPI
   |
   +---- PostgreSQL
   |
   +---- LocalStorage
   |
   +---- Redis/Celery
             |
             +---- ingest queue
             |
             +---- faces queue
             |
             +---- match queue
             |
             +---- maintenance queue
```

Processing:

```text
UPLOAD
  ↓
temporary file
  ↓
SHA-256 + validation
  ↓
Photos row
  ↓
commit
  ↓
Celery task
  ↓
claim photo
  ↓
generate web/thumb
  ↓
InsightFace detection
  ↓
PhotoFaces
  ↓
mark event dirty
  ↓
BATCH MATCH
  ↓
Matches
  ↓
Gallery / Review
```

---

# 9. AI ENGINE BOUNDARY

Do NOT make an HTTP request to an AI service for every photo.

InsightFace must be loaded inside the face worker process.

Create a shared module such as:

```text
backend/services/face_engine.py
```

or the equivalent architecture already used by the project.

The worker must initialize the model once per worker process.

Use:

```text
FaceAnalysis(name="buffalo_l")
```

The model must be initialized through the worker-process lifecycle.

Do not initialize InsightFace once per task.

Do not initialize InsightFace once per image.

Week 1 and Week 2 must use:

```text
same model
same model version
same normalization
same quality utilities
same embedding representation
```

Before matching begins, verify Week 1 embeddings are:

```text
512 dimensions
finite
model-versioned
L2 normalized
```

If they are not normalized, create:

```text
scripts/backfill_normalize_embeddings.py
```

and normalize them once.

Never mix normalized and raw vectors.

The matrix loader must assert:

```text
abs(norm(vector) - 1.0) <= 1e-3
```

and fail loudly if this is violated.

This compatibility requirement is explicitly locked in the reviewed design.

---

# 10. DAY 8 — DATABASE + STORAGE + UPLOAD

## Goal

Build the complete photo ingestion foundation.

---

## 10.1 Create database tables

Create Alembic migrations for:

```text
UploadBatches
Photos
PhotoFaces
Matches
MatchRuns
```

---

# 11. UploadBatches

Use:

```text
UploadBatches
-------------
id
event_id
created_by
total_files
received_files
duplicate_files
rejected_files
status
created_at
completed_at
```

Do NOT store:

```text
processed_files
failed_files
faces_found
matches_created
```

as mutable counters.

Those values must be derived from database queries.

Reason:

Multiple workers updating the same counters creates race conditions and permanent counter drift.

Instead:

```text
processed_files
failed_files
faces_found
matches_created
```

are calculated from Photos and PhotoFaces.

The reviewed design specifically locks progress as derived data.

---

# 12. Photos schema

Create:

```text
Photos
------
id
event_id
batch_id
uploaded_by

original_filename

storage_key
web_key
thumb_key

content_hash
mime_type
file_size

width
height

exif_taken_at

status
face_count

processing_error
attempts

created_at
processed_at
updated_at
```

Add:

```text
UNIQUE(event_id, content_hash)
```

Add:

```text
INDEX(event_id, status)
INDEX(batch_id, status)
```

---

# 13. Photo status state machine

Use:

```text
pending
queued
processing
processed
failed
```

Do NOT use:

```text
skipped_duplicate
```

A duplicate must not create a Photo row.

Correct state flow:

```text
pending
   ↓
queued
   ↓
processing
   ↓
processed
```

Failure:

```text
processing
   ↓
failed
   ↓
queued
   ↓
processing
```

Maximum attempts:

```text
3
```

After the third failed attempt:

```text
failed
```

terminal state.

---

# 14. Atomic upload/dedup algorithm

This is mandatory.

When uploading a photo:

### Step 1

Create a temporary file.

Example:

```text
/tmp/event-upload-<uuid>.tmp
```

### Step 2

Stream the request in chunks.

Chunk size:

```text
1 MB
```

Never do:

```python
await file.read()
```

for the complete photo.

Never buffer a 25 MB image in memory unnecessarily.

---

### Step 3

While streaming:

Calculate:

```text
SHA-256
bytes_received
```

and enforce:

```text
MAX_PHOTO_MB=25
```

---

### Step 4

Validate magic bytes.

Accepted formats:

```text
JPEG
PNG
HEIC
```

Do NOT trust:

```text
filename extension
Content-Type header
```

alone.

A file named:

```text
virus.exe.jpg
```

must not be accepted as an image merely because of the extension.

---

### Step 5

Attempt:

```text
INSERT Photos(event_id, content_hash, ...)
```

The unique constraint handles concurrent duplicate uploads.

---

### Step 6 — duplicate

If:

```text
(event_id, content_hash)
```

already exists:

```text
delete temporary file

return HTTP 200
{
    "duplicate": true,
    "photo_id": existing_photo_id
}
```

Do not:

```text
return 409
create another Photo
enqueue processing
```

---

### Step 7 — new photo

If insertion succeeds:

```text
COMMIT database transaction
```

Only after commit:

```text
move temp file → final storage key
enqueue Celery task
```

Do not enqueue before database commit.

This prevents orphaned processing jobs.

The atomic upload flow and removal of `skipped_duplicate` are explicit locked decisions.

---

# 15. Storage abstraction

Create:

```python
class StorageBackend:
    put(...)
    get(...)
    delete(...)
    exists(...)
```

or equivalent.

Implement:

```text
LocalStorage
```

Nothing outside StorageBackend should directly manipulate storage files.

Future Week 4/production storage must be replaceable without rewriting photo-processing code.

---

# 16. Storage key layout

Use exactly:

```text
events/{event_id}/photos/{photo_id}/original.{ext}

events/{event_id}/photos/{photo_id}/web.jpg

events/{event_id}/photos/{photo_id}/thumb.jpg

events/{event_id}/photos/{photo_id}/faces/{photo_face_id}.jpg
```

Original extension must be preserved.

Examples:

```text
original.jpg
original.png
original.heic
```

Never store a PNG or HEIC original as:

```text
original.jpg
```

Web/thumb/crops:

```text
JPEG
quality 82
```

The original reviewed specification explicitly requires true original extensions.

---

# 17. HEIC

HEIC is supported.

Use:

```text
pillow-heif
```

Initialize:

```python
register_heif_opener()
```

at image-engine initialization.

Do not leave HEIC implementation to guesswork.

---

# 18. API — upload

Implement:

```http
POST /events/{event_id}/photos
```

Authentication required.

Verify:

```text
JWT user owns event
```

Request:

```text
multipart/form-data
file
batch_id optional
```

Response:

```json
{
  "photo_id": "...",
  "duplicate": false
}
```

or:

```json
{
  "photo_id": "...",
  "duplicate": true
}
```

Never return:

```text
storage_key
absolute filesystem path
embedding
```

---

# 19. Upload batch API

Implement:

```http
POST /events/{event_id}/upload-batches
```

Returns:

```json
{
  "batch_id": "...",
  "status": "active"
}
```

Implement:

```http
GET /upload-batches/{batch_id}
```

Return derived:

```json
{
  "total_files": 5000,
  "received_files": 4980,
  "duplicate_files": 25,
  "rejected_files": 5,
  "processed_files": 3200,
  "failed_files": 2,
  "faces_found": 12800,
  "matches_created": 11500,
  "status": "processing"
}
```

The exact response schema can be adapted to existing conventions.

---

# 20. Photo listing API

Implement:

```http
GET /events/{event_id}/photos
```

Use keyset pagination.

Do NOT use:

```text
OFFSET 10000
```

for the main infinite-scroll query.

Support filters:

```text
status
face_count_zero
```

Return metadata only.

Do not return embeddings.

---

# 21. DAY 9 — CELERY + REDIS

Install/configure:

```text
Celery
Redis
Celery Beat
Flower
```

Queues:

```text
ingest
faces
match
maintenance
```

Create separate worker processes/services where practical.

Docker services:

```text
redis
worker-faces
worker-match
beat
flower
```

---

# 22. Celery reliability configuration

These settings are mandatory:

```text
task_acks_late = True

worker_prefetch_multiplier = 1

task_reject_on_worker_lost = True

task_time_limit = 300

task_soft_time_limit = 240

visibility_timeout = 600

max_retries = 3
```

Retries:

```text
exponential backoff
jitter
maximum 3 retries
```

---

# 23. NEVER trust Celery for exactly-once execution

Celery can deliver the same task more than once.

Therefore the database is the source of truth.

Photo processing must claim the row atomically.

Use logic equivalent to:

```sql
UPDATE photos
SET
    status = 'processing',
    attempts = attempts + 1,
    updated_at = NOW()
WHERE
    id = :photo_id
    AND status IN ('pending', 'queued', 'failed')
    AND attempts < 3
RETURNING id;
```

If zero rows are returned:

```text
another worker already owns it
OR
it is already complete
OR
attempt limit reached
```

Exit silently.

Do not process it.

---

# 24. Stale worker recovery

Celery Beat must periodically find:

```text
status = processing
updated_at < now - 10 minutes
attempts < 3
```

and set:

```text
status = queued
```

Then requeue the task.

If:

```text
attempts >= 3
```

mark:

```text
failed
```

This prevents infinite retry loops.

The state-machine requirements are explicitly specified in the source plan.

---

# 25. Pipeline status endpoint

Implement:

```http
GET /events/{event_id}/pipeline-status
```

Return aggregate state.

Example:

```json
{
  "photos": {
    "pending": 100,
    "queued": 50,
    "processing": 8,
    "processed": 4800,
    "failed": 2
  },
  "faces": {
    "total": 24000,
    "matchable": 22000,
    "non_matchable": 2000
  },
  "matches": {
    "confirmed": 18000,
    "review": 3000,
    "rejected": 1000
  }
}
```

---

# 26. DAY 10 — PHOTO FACE EXTRACTION

Create:

```text
extract_faces(photo_id)
```

Celery task.

---

# 27. Processing order

For a claimed photo:

```text
load original
   ↓
decode image
   ↓
apply EXIF orientation
   ↓
generate web derivative
   ↓
generate thumbnail
   ↓
run face detection on web derivative
   ↓
generate embedding for each face
   ↓
quality evaluation
   ↓
persist PhotoFaces
   ↓
commit
   ↓
mark photo processed
   ↓
mark event faces dirty
```

Do NOT run detection against the original.

Detection runs against:

```text
web derivative
```

with long edge:

```text
1600 px
```

Thumbnail:

```text
400 px
```

JPEG:

```text
quality=82
```

---

# 28. Image safety

Set:

```text
MAX_IMAGE_PIXELS=50000000
```

or configurable environment variable.

Protect against decompression bombs.

A small compressed image must not be allowed to decode into an enormous image.

Also enforce:

```text
MAX_PHOTO_MB=25
```

File size and decoded pixel count are separate protections.

---

# 29. EXIF

Respect EXIF orientation.

After orientation correction:

```text
web image = canonical coordinate system
```

Strip EXIF metadata from:

```text
web
thumb
face crops
```

But preserve:

```text
DateTimeOriginal
```

into:

```text
Photos.exif_taken_at
```

---

# 30. InsightFace

Use:

```text
buffalo_l
```

Detection:

```text
det_size=(640,640)
```

Load model once per worker process.

CPU configuration:

```text
4 worker processes
1 ONNX intra-op thread per worker
```

Do not launch 12 model workers on a machine with 4 GB RAM.

Approximate budget:

```text
~500 MB RSS per worker
~2 GB for 4 workers
```

Document this.

---

# 31. PhotoFaces schema

Create:

```text
PhotoFaces
----------
id
photo_id
event_id

bbox_x
bbox_y
bbox_w
bbox_h

det_score

embedding
model_version
embedding_dim

quality_score
blur_score
face_area_ratio
yaw
pitch
roll

is_matchable
quality_flags

crop_key

matched_at

created_at
updated_at
```

---

# 32. Embedding storage

Embedding:

```text
vector(512)
```

must be:

```text
float32
L2 normalized
```

at write time.

Never store mixed raw/normalized vectors.

Map embedding through SQLAlchemy as deferred.

Example concept:

```python
embedding = deferred(...)
```

Gallery queries must never accidentally load thousands of 512-dimensional vectors.

The reviewed design specifically requires deferred embeddings and explicit matrix loading.

---

# 33. Bounding boxes

Bounding boxes must be normalized.

Store:

```text
bbox_x
bbox_y
bbox_w
bbox_h
```

as floats:

```text
0.0 → 1.0
```

relative to the EXIF-corrected web image.

Example:

```text
bbox_x = left / web_width
bbox_y = top / web_height
bbox_w = width / web_width
bbox_h = height / web_height
```

Never store pixel coordinates.

Never store coordinates relative to the original image.

This prevents overlay bugs.

---

# 34. Face crops

For every detected face:

Create a padded square crop.

Parameters:

```text
~15% padding
256px long edge
JPEG
quality 82
```

Save:

```text
events/{event_id}/photos/{photo_id}/faces/{photo_face_id}.jpg
```

Store:

```text
crop_key
```

in PhotoFaces.

The review UI must use this crop.

Do NOT crop the original image on every review request.

---

# 35. Quality evaluation

Reuse Week 1 quality utilities.

BUT:

Week 1:

```text
quality = gate
```

Week 2:

```text
quality = flag
```

Low-quality faces must still be stored.

Examples:

```text
det_score < 0.5
face_area_ratio < 0.5%
blur below threshold
abs(yaw) > 45°
```

A face can have multiple problems.

Therefore:

```text
quality_flags = []
```

should support multiple values.

Example:

```json
[
  "low_detection_score",
  "too_small",
  "blurry"
]
```

If a face is not suitable for matching:

```text
is_matchable = false
```

but still persist the row.

Do not discard it.

---

# 36. Extraction idempotency

This is mandatory.

Failure scenario:

```text
Worker starts
↓
detects 8 faces
↓
inserts 8 PhotoFaces
↓
worker crashes
↓
photo remains processing
↓
photo gets retried
```

Without protection:

```text
16 PhotoFaces
```

would be created.

Correct behavior:

After successfully claiming the photo:

```sql
DELETE FROM photo_faces
WHERE photo_id = :photo_id;
```

Then insert fresh rows inside the same processing transaction.

Only after the transaction commits should matching become eligible.

This exact delete-before-insert rule is locked.

---

# 37. Match triggering — CRITICAL

## DO NOT DO THIS

```text
photo 1 → match
photo 2 → match
photo 3 → match
...
photo 5000 → match
```

This is forbidden.

Do not create 5,000 MatchRuns for a 5,000-photo upload.

---

# 38. Correct matching architecture

When face extraction finishes:

Set:

```text
Redis:
event:{event_id}:faces_dirty = true
```

Do not immediately run a full match.

Celery Beat every:

```text
30 seconds
```

checks dirty events.

Also allow the batch-completion handler to request matching.

Use a Redis lock:

```text
SET event:{event_id}:match_lock <token> NX EX 600
```

Only one event-level match run can execute at once.

Scope:

```text
PhotoFaces where
is_matchable = true
AND matched_at IS NULL
```

This is the matching watermark.

One matrix load.

One batched NumPy operation.

One meaningful MatchRun.

This is one of the most important Week 2 architectural requirements.

---

# 39. PhotoFaces matched_at

Add:

```text
matched_at TIMESTAMPTZ NULL
```

Index:

```text
INDEX(event_id, is_matchable, matched_at)
```

When a face has been successfully considered by the matching pipeline:

```text
matched_at = now()
```

A threshold re-run can reset:

```text
matched_at = NULL
```

for its selected scope.

This avoids scanning all 25,000 faces every 30 seconds.

---

# 40. DAY 11 — MATCHING ENGINE

Create:

```text
MatchingService
```

with:

```text
match_pending_faces(event_id)
match_guest(event_id, guest_id)
match_event(event_id)
```

The important production path is:

```text
match_pending_faces(event_id)
```

---

# 41. Reference matrix — IMPORTANT CORRECTION

Do NOT construct the reference matrix as:

```text
500 guests × 512
```

because a guest may have multiple reference embeddings.

Correct matrix:

```text
R =
number_of_reference_embeddings
×
512
```

Example:

```text
500 guests
×
2 references average
=
1000 reference embeddings
```

So:

```text
R = 1000 × 512
```

Maintain a parallel array:

```text
reference_guest_ids
```

Example:

```text
row 0 → guest A
row 1 → guest A
row 2 → guest B
row 3 → guest C
row 4 → guest C
```

---

# 42. Multi-reference scoring

For each photo face:

```text
similarity = F @ R.T
```

Then aggregate:

```text
guest_score =
MAX(similarity across all reference embeddings belonging to guest)
```

Do NOT average references.

Do NOT choose the first reference.

Do NOT treat references as separate guests.

The score is:

```text
max(reference similarity for guest)
```

---

# 43. Top-2 margin — DISTINCT GUESTS

This is critical.

Suppose:

```text
Guest A reference 1 = 0.48
Guest A reference 2 = 0.47
Guest B reference 1 = 0.43
```

Do NOT calculate:

```text
0.48 - 0.47 = 0.01
```

because both are Guest A.

Correct aggregation:

```text
Guest A = 0.48
Guest B = 0.43
```

Margin:

```text
0.48 - 0.43 = 0.05
```

Therefore:

**Top-2 means top-2 distinct guest IDs after aggregation.**

This is explicitly locked by the reviewed specification.

---

# 44. Matching algorithm

Load reference embeddings from PostgreSQL.

Build:

```text
R: float32 [n_reference_embeddings, 512]

guest_ids:
int32 [n_reference_embeddings]
```

Load photo-face embeddings in chunks:

```text
4096 faces
```

Use a server-side cursor.

For each chunk:

```python
S = F @ R.T
```

Then aggregate per guest.

Use efficient NumPy operations.

Do NOT perform:

```sql
ORDER BY embedding <=> :face
```

for every face.

That would produce thousands of database round trips.

At this scale:

```text
NumPy matrix multiplication
```

is the required implementation.

---

# 45. Matching thresholds

Initial defaults:

```text
AUTO_CONFIRM = 0.42
REVIEW_FLOOR = 0.32
MARGIN = 0.05
```

Decision:

```text
score >= 0.42
AND
margin >= 0.05
→ auto_confirmed
```

```text
score >= 0.32
AND
score < 0.42
→ review
```

```text
score < 0.32
→ rejected
```

AND:

```text
margin < 0.05
→ review
```

regardless of absolute score.

These are starting values only.

Day 14 calibration replaces them.

---

# 46. Event-level threshold configuration

Events get:

```text
match_threshold nullable
review_floor nullable
match_margin nullable
```

If NULL:

use environment defaults.

Priority:

```text
Event override
    ↓
Environment default
```

Every Match stores the threshold used for auditability.

---

# 47. Matches table — FINAL SEMANTICS

A Match row represents:

> The current algorithmic/manual assignment result for ONE photo face.

Therefore:

```text
UNIQUE(photo_face_id)
```

is mandatory.

Do NOT use:

```text
UNIQUE(guest_id, photo_face_id)
```

because that allows the same face to belong to multiple guests.

There must be at most one current assignment per photo face.

The reviewed design explicitly changes this constraint.

---

# 48. Matches schema

Use:

```text
Matches
-------
id

event_id
guest_id
photo_id
photo_face_id

match_run_id

similarity
threshold_used

decision

status

second_guest_id
second_similarity
margin
review_reason

top_candidates

model_version

matched_at

reviewed_by
reviewed_at

created_at
updated_at
```

Enums:

```text
decision:
auto_confirmed
review
rejected
```

```text
status:
active
rejected_by_organizer
manually_added
```

---

# 49. Top candidates

Do NOT create a separate MatchCandidates table for Week 2.

Use:

```text
Matches.top_candidates JSONB
```

This is intentionally chosen to keep Week 2 simpler.

Example:

```json
[
  {
    "guest_id": "guest-a",
    "score": 0.48,
    "rank": 1
  },
  {
    "guest_id": "guest-b",
    "score": 0.43,
    "rank": 2
  },
  {
    "guest_id": "guest-c",
    "score": 0.39,
    "rank": 3
  }
]
```

Store top 3 distinct guests.

The final reviewed design selected JSONB instead of another table.

---

# 50. Match debug fields

Persist:

```text
second_guest_id
second_similarity
margin
review_reason
match_run_id
```

Possible:

```text
review_reason = below_margin
```

or:

```text
review_reason = in_review_band
```

This lets the UI explain:

```text
Score: 0.44
Second-best: 0.43
Margin: 0.01
Reason: in_review_band
```

Do not store duplicate threshold fields such as:

```text
review_floor_used
margin_used
```

inside Match.

Those are already recoverable from:

```text
MatchRun.params
```

The review explicitly trimmed those redundant fields.

---

# 51. MatchRuns

Create:

```text
MatchRuns
---------
id
event_id

trigger
scope

params

faces_scanned
guests_scanned

auto_confirmed
sent_to_review
rejected

protected_rows

status
error

started_at
finished_at
created_at
```

Triggers:

```text
photo_ingest
guest_registered
manual_rerun
threshold_change
```

Scopes:

```text
full_event
new_photos
new_guests
```

---

# 52. Protected manual decisions

This is mandatory.

Suppose organizer manually confirms:

```text
photo face 123 → Guest A
```

Later threshold changes.

A re-run must NOT overwrite that decision.

Re-runs may update only rows where:

```text
reviewed_at IS NULL
AND status = active
```

Protected:

```text
reviewed_at IS NOT NULL
status = manually_added
status = rejected_by_organizer
```

These rows must be counted as:

```text
protected_rows
```

inside MatchRuns.

---

# 53. Force override

Only explicit:

```http
POST /events/{event_id}/match-runs
```

with:

```json
{
  "force": true
}
```

may override protected rows.

Do not silently overwrite organizer work.

This protection is explicitly required.

---

# 54. Guest registration while photos already exist

This is mandatory.

Scenario:

```text
Event already has 5,000 photos.

Guest #501 registers.
```

The new guest must be matched against existing matchable PhotoFaces.

Implement:

```text
match_guest(event_id, guest_id)
```

Target:

```text
≤ 1 second
```

for approximately 25,000 existing faces.

Do NOT require the photographer to re-upload photos.

---

# 55. Guest matrix cache

Cache the reference matrix in Redis.

Use a derived fingerprint.

Do NOT use:

```text
event:{id}:guest_matrix:v{count}
```

because embedding updates can happen without changing count.

Use a fingerprint based on:

```text
count
max(face_embeddings.id)
max(face_embeddings.updated_at)
```

for all reference embeddings belonging to the event's guests.

Example:

```text
event:{event_id}:refmatrix:{fingerprint}
```

TTL:

```text
1 hour
```

The cache is allowed to expire naturally.

This avoids a manually maintained version counter becoming stale.

---

# 56. Matrix load safety

Whenever the reference matrix loads:

```text
assert dimensions == 512
assert finite
assert norm ~= 1
```

Failure must be loud.

Never silently normalize the entire matrix at load time.

If normalization is needed:

fix the source embeddings using the migration/backfill.

---

# 57. pgvector usage

At this scale:

**Do not create an ANN index yet.**

Do not use HNSW for the full matching workload.

Exact NumPy matching is preferred.

Keep pgvector available for:

```http
GET /photo-faces/{id}/candidates
```

single-face/ad-hoc lookup.

Only consider HNSW when:

```text
>100,000 PhotoFaces for one event
```

At that point document/use:

```sql
CREATE INDEX CONCURRENTLY idx_photo_faces_embedding_hnsw
ON photo_faces
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 16,
    ef_construction = 64
);
```

Do not activate this index during the normal 25k-face Week 2 test.

---

# 58. DAY 12 — BULK UPLOADER UI

Create:

```text
/events/{event_id}/upload
```

Features:

* drag/drop
* folder selection
* multi-select
* client-side file validation
* max 25 MB
* JPEG/PNG/HEIC only
* six concurrent uploads
* per-file progress
* retry individual
* retry all failed
* cancel remaining
* duplicate state
* failed state
* completed state

---

# 59. IMPORTANT — 5,000-row UI

Do NOT render:

```tsx
files.map(...)
```

for 5,000 files.

Use:

```text
@tanstack/react-virtual
```

to virtualize the list.

Only render visible rows.

---

# 60. Upload state

Each file should have:

```text
queued
uploading
done
duplicate
failed
```

Example:

```text
IMG_001.jpg     100%    done
IMG_002.jpg     100%    duplicate
IMG_003.jpg      62%    uploading
IMG_004.jpg       0%    queued
IMG_005.jpg       -     failed
```

---

# 61. Browser refresh behavior

Do not pretend to implement resumable local file uploads.

If browser refreshes:

```text
already-uploaded files remain on server
server processing continues
```

But files that were never sent cannot magically resume after refresh.

The UI should reload:

```text
batch state
```

from the server.

This is the intended Week 2 contract.

---

# 62. Batch polling

Poll:

```http
GET /upload-batches/{batch_id}
```

every:

```text
2 seconds
```

while active.

No WebSockets.

No SSE.

No live streaming infrastructure.

Calculate:

```text
uploaded
processed
failed
faces_found
matches_created
ETA
```

ETA:

Use rolling throughput rather than a fixed estimate.

---

# 63. DAY 13 — PHOTO GRID

Create:

```text
/events/{event_id}/photos
```

Use:

```text
keyset pagination
```

Features:

* thumbnail grid
* infinite scroll
* lazy-loaded images
* status filter
* zero-face filter
* photo detail modal

Never load all 5,000 images at once.

---

# 64. Photo detail modal

Show:

```text
photo
bounding boxes
detected faces
matched guest
similarity
decision
```

Bounding boxes must be calculated from normalized coordinates.

Each face should show:

```text
Guest: John
Score: 0.47
Decision: Auto-confirmed
```

or:

```text
Guest: Unknown
Decision: Rejected
```

---

# 65. Guest gallery

Extend:

```text
/guests/{guest_id}
```

with:

```text
Matched Photos
```

Show:

* thumbnail
* score
* decision
* confirmed/review split

Gallery source query:

```text
Matches.status IN ('active', 'manually_added')
AND Matches.decision = 'auto_confirmed'
```

A review match must not appear in the confirmed gallery.

A rejected match must not appear.

---

# 66. Remove from gallery

Organizer can remove a photo from a guest gallery.

Do NOT delete:

```text
Photo
PhotoFace
```

Instead:

```text
Matches.status = rejected_by_organizer
```

This preserves processing history.

---

# 67. Review queue

Create:

```text
/events/{event_id}/review
```

Show:

```text
face crop
top candidate
candidate #2
candidate #3
scores
margin
reason
```

Actions:

```text
Confirm
Reject
Assign Guest
```

---

# 68. Keyboard controls

Organizer will potentially review hundreds of faces.

Support:

```text
Arrow Left  → previous
Arrow Right → next
Enter       → confirm
R           → reject
```

or equivalent intuitive keyboard shortcuts.

Do not make the reviewer click through unnecessary modal flows.

---

# 69. Manual assign

Implement:

```http
POST /matches
```

Conceptually:

```json
{
  "photo_face_id": "...",
  "guest_id": "..."
}
```

This updates the existing Match row.

Do NOT create another Match row for the same PhotoFace.

Result:

```text
status = manually_added
```

---

# 70. Confirm/reject API

Implement:

```http
PATCH /matches/{match_id}
```

Possible actions:

```text
confirm
reject
```

When organizer acts:

```text
reviewed_by = current_user
reviewed_at = now()
```

Manual decisions become protected from future automatic re-runs.

---

# 71. DAY 14 — CALIBRATION

Do not blindly assume:

```text
0.42
0.32
```

are production thresholds.

They are only starting values.

Calibration must use real labeled data.

---

# 72. Better calibration method

Do not spend the entire afternoon manually labeling arbitrary pairs.

Instead:

Take approximately:

```text
50 real event photos
~200 detected faces
```

Label the identity of each face.

Then generate genuine/impostor pairs combinatorially.

This produces thousands of pairs from a manageable amount of human labeling.

Mine hard negatives:

```text
highest-scoring pairs
with different identities
```

and manually verify them.

---

# 73. Calibration sweep

Sweep:

```text
0.25 → 0.55
step = 0.01
```

Calculate:

```text
FMR
FNMR
precision
recall
```

Select an operating point with:

```text
FMR <= 1%
```

Bias toward precision.

Reason:

```text
Wrong person's photo
→ privacy incident

Missing a photo
→ inconvenience
```

---

# 74. Calibration documentation

Create:

```text
docs/calibration.md
```

Document:

```text
model_version
dataset description
number of labeled faces
number of genuine pairs
number of impostor pairs

threshold
FMR
FNMR
precision
recall

chosen auto-confirm threshold
review floor
margin
expected review volume / 1000 faces
```

Also record the calibration curve.

The source specification requires this calibration to be documented and based on identity labels/hard negatives.

---

# 75. PERFORMANCE TARGETS

These are hard acceptance criteria.

## Upload

```text
5,000 files
~4 MB average
~20 GB total
≤45 minutes
100 Mbit LAN
6 concurrent uploads
```

---

## Face processing

```text
5,000 photos
~25,000 faces

≤30 minutes
8 vCPU CPU-only

≤6 minutes
one GPU
```

CPU:

```text
4 worker processes
1 ONNX thread
```

---

## Matching

```text
25,000 faces × 500 guests
≤5 seconds
```

Use:

```text
NumPy matrix multiplication
```

not:

```text
25,000 SQL similarity queries
```

---

## New guest matching

```text
1 guest × 25,000 faces
≤1 second
```

---

## Gallery

Target:

```text
60 thumbnails
≤800 ms p95
```

Use keyset pagination.

---

# 76. API ENDPOINTS

Implement at minimum:

```text
POST   /events/{event_id}/upload-batches
GET    /upload-batches/{batch_id}

POST   /events/{event_id}/photos
GET    /events/{event_id}/photos
DELETE /photos/{photo_id}

GET    /events/{event_id}/pipeline-status

POST   /events/{event_id}/match-runs
GET    /match-runs/{match_run_id}

GET    /events/{event_id}/matches
GET    /photo-faces/{photo_face_id}/candidates

GET    /guests/{guest_id}/photos

PATCH  /matches/{match_id}
POST   /matches

GET    /media/photos/{photo_id}/original
GET    /media/photos/{photo_id}/web
GET    /media/photos/{photo_id}/thumb
GET    /media/faces/{photo_face_id}
```

All endpoints must follow the existing authentication architecture.

---

# 77. MEDIA SECURITY

Never return:

```text
/data/storage/...
```

or:

```text
events/<id>/photos/<id>/original.jpg
```

directly in normal API JSON.

Use authenticated endpoints.

For every media request:

1. Authenticate JWT.
2. Load requested object.
3. Verify event ownership.
4. Verify requested storage key belongs to that object.
5. Validate key against canonical storage-key format.
6. Reject path traversal.
7. Serve file.

Test:

```text
Organizer A cannot access Organizer B's image.
```

even if Organizer A guesses the URL.

---

# 78. PHOTO DELETE

Implement:

```http
DELETE /photos/{photo_id}
```

Steps:

```text
authenticate
↓
verify event ownership
↓
delete Photo
↓
cascade PhotoFaces
↓
cascade Matches
↓
commit
↓
delete original
↓
delete web
↓
delete thumb
↓
delete face crops
```

Storage deletion can happen after database commit.

Do not allow another organizer to delete the photo.

---

# 79. CASCADE RULES

Deleting a photo:

```text
Photo
 ├── PhotoFaces
 │     └── Matches
```

All should disappear.

Deleting a guest:

```text
Guest
 └── Matches
```

Matches disappear.

But:

```text
PhotoFaces
```

must remain.

Why?

The face exists in the event photo independently of whether the guest still exists.

Test both behaviors.

---

# 80. INDEXES

Create:

```text
Photos:
INDEX(event_id, status)
INDEX(batch_id, status)

PhotoFaces:
INDEX(event_id, is_matchable, matched_at)

Matches:
UNIQUE(photo_face_id)
INDEX(guest_id, status, similarity DESC)

Review:
partial INDEX(event_id, decision)
WHERE decision = 'review'
```

Do not create unnecessary indexes on large vector columns during Week 2.

---

# 81. ORM PERFORMANCE

Embedding fields:

```text
FaceEmbeddings.embedding
PhotoFaces.embedding
```

must be deferred.

Gallery queries should retrieve:

```text
photo metadata
thumbnail key
guest
similarity
decision
```

not:

```text
all vectors
```

A normal gallery query should never move ~51 MB of vectors from PostgreSQL into Python/SQLAlchemy just to render thumbnails.

---

# 82. SEED / LOAD TEST

Create:

```text
scripts/seed_scale.py
```

It must create:

```text
1 event
500 guests
reference embeddings
5,000 photos
```

Target:

```text
~25,000 faces
```

The script must be capable of running the entire pipeline.

Do not fake the database workload with only 10 photos.

The final test must actually exercise:

```text
500 guests
5,000 photos
~25k faces
```

---

# 83. BENCHMARK SCRIPT

Create:

```text
scripts/bench_faces.py
```

Output:

```text
images processed
faces detected
images/sec
faces/sec
projected 5,000-photo runtime
```

Example:

```text
Processed: 500
Faces: 2,021
Images/sec: 3.02
Faces/sec: 12.1
Projected 5,000 runtime: 27m 35s
Budget: 30m
PASS
```

---

# 84. REQUIRED TESTS

## Upload

* [ ] normal JPEG
* [ ] normal PNG
* [ ] normal HEIC
* [ ] duplicate upload
* [ ] concurrent duplicate upload
* [ ] corrupt JPEG
* [ ] truncated JPEG
* [ ] renamed EXE
* [ ] oversized file
* [ ] file at exact size limit
* [ ] upload failure does not kill batch

---

# 85. Worker tests

* [ ] worker processes photo
* [ ] worker killed during processing
* [ ] worker restarts
* [ ] same photo is not processed twice
* [ ] Redis restart
* [ ] task redelivery
* [ ] attempts increment atomically
* [ ] stale processing gets requeued
* [ ] third failure becomes terminal
* [ ] no duplicate PhotoFaces

---

# 86. Face extraction tests

* [ ] zero faces
* [ ] one face
* [ ] multiple faces
* [ ] 25 faces
* [ ] blurry face
* [ ] tiny face
* [ ] rotated face
* [ ] dark face
* [ ] multiple quality flags
* [ ] normalized bbox
* [ ] face crop created
* [ ] crop key stored
* [ ] EXIF orientation correct
* [ ] web derivative created
* [ ] thumb derivative created

---

# 87. Matching tests

* [ ] one obvious match
* [ ] no match
* [ ] review-band match
* [ ] low-margin match
* [ ] two guests with similar faces
* [ ] one guest with multiple reference embeddings
* [ ] top-2 correctly uses distinct guest IDs
* [ ] no NaN
* [ ] normalized vectors
* [ ] same MatchRun twice does not create duplicate rows
* [ ] same PhotoFace cannot have two Match rows
* [ ] threshold re-run changes unreviewed decisions
* [ ] threshold re-run preserves manual decisions

---

# 88. Critical multi-reference test

Create:

```text
Guest A:
reference 1 = 0.48
reference 2 = 0.47

Guest B:
reference 1 = 0.43
```

Expected:

```text
Guest A score = 0.48
Guest B score = 0.43

margin = 0.05
```

NOT:

```text
margin = 0.01
```

This test must exist.

---

# 89. Manual-review tests

Test:

```text
algorithm says Guest A
organizer changes to Guest B
threshold changes
re-run
```

Expected:

```text
Guest B remains.
```

Test:

```text
organizer rejects
threshold changes
re-run
```

Expected:

```text
rejected state remains.
```

Only:

```text
force=true
```

can override.

---

# 90. Security tests

* [ ] no JWT → 401
* [ ] wrong organizer → 403/404
* [ ] direct storage-key access denied
* [ ] path traversal rejected
* [ ] storage keys never leak in JSON
* [ ] embeddings never appear in JSON
* [ ] photo ownership checked
* [ ] guest/event ownership checked
* [ ] upload rate limit
* [ ] maximum upload size enforced server-side
* [ ] MIME/magic-byte validation server-side

---

# 91. API EMBEDDING LEAK TEST

Write an automated test that examines all Week 2 API responses.

Assert that responses do not contain:

```text
embedding
vector
embedding_data
```

or actual vector arrays.

The embedding must remain internal.

This extends Week 1's existing security requirement.

---

# 92. ENVIRONMENT VARIABLES

Add:

```text
REDIS_URL

CELERY_BROKER_URL
CELERY_RESULT_BACKEND

FACE_WORKER_CONCURRENCY
ONNX_INTRA_OP_THREADS

INSIGHTFACE_MODEL=buffalo_l
INSIGHTFACE_DET_SIZE=640
USE_GPU=false

MATCH_THRESHOLD=0.42
MATCH_REVIEW_FLOOR=0.32
MATCH_MARGIN=0.05

MAX_PHOTO_MB=25
MAX_IMAGE_PIXELS=50000000

WEB_IMAGE_MAX_EDGE=1600
THUMB_MAX_EDGE=400

STORAGE_BACKEND=local
STORAGE_ROOT=/data/storage
```

Document every variable.

---

# 93. DOCKER COMPOSE

The complete Week 2 stack must include:

```text
frontend
backend
postgres
redis
worker-faces
worker-match
beat
flower
```

AI dependencies must be available to the worker.

`docker-compose up` must start the platform.

No manual:

```text
pip install
npm install
redis-server
celery -A ...
```

steps should be required after following the README.

---

# 94. DATABASE PERFORMANCE

Document recommended PostgreSQL settings:

```text
work_mem = 64MB
maintenance_work_mem = 512MB
```

Do not blindly hard-code inappropriate `shared_buffers`.

Document the recommended value for the developer machine.

---

# 95. FILE STRUCTURE

Adapt to the existing Week 1 structure, but the result should approximately contain:

```text
backend/
├── api/
│   └── endpoints/
│       ├── photos.py
│       ├── uploads.py
│       ├── matches.py
│       ├── media.py
│       └── pipeline.py
│
├── models/
│   ├── upload_batch.py
│   ├── photo.py
│   ├── photo_face.py
│   ├── match.py
│   └── match_run.py
│
├── schemas/
│   ├── photo.py
│   ├── upload_batch.py
│   ├── match.py
│   └── match_run.py
│
├── services/
│   ├── storage/
│   │   ├── base.py
│   │   └── local.py
│   ├── face_engine.py
│   ├── photo_processor.py
│   ├── matching_service.py
│   └── matrix_cache.py
│
├── workers/
│   ├── celery_app.py
│   ├── faces.py
│   ├── matching.py
│   └── maintenance.py
│
└── repositories/
    ├── photos.py
    ├── photo_faces.py
    ├── matches.py
    └── match_runs.py

frontend/
├── app/
│   └── events/
│       └── [id]/
│           ├── upload/
│           ├── photos/
│           └── review/
│
├── components/
│   ├── uploader/
│   ├── photo-grid/
│   ├── face-review/
│   └── batch-progress/
│
└── services/
    ├── photos.ts
    ├── uploads.ts
    └── matches.ts

scripts/
├── seed_scale.py
├── bench_faces.py
└── backfill_normalize_embeddings.py

docs/
├── calibration.md
├── scaling.md
└── week2.md
```

Do not destroy the existing Week 1 organization just to match this example.

---

# 96. MATCHING PSEUDOCODE

The core matching implementation should conceptually behave like:

```python
references, guest_ids = load_reference_matrix(event_id)

assert references.shape[1] == 512
assert all_vectors_finite(references)
assert_norms_close_to_one(references)

pending_faces = load_pending_faces(
    event_id,
    chunk_size=4096
)

for faces in pending_faces:

    F = faces.embeddings

    assert F.shape[1] == 512
    assert all_vectors_finite(F)
    assert_norms_close_to_one(F)

    similarity_matrix = F @ references.T

    # aggregate reference rows by guest
    guest_scores = aggregate_max_by_guest(
        similarity_matrix,
        guest_ids
    )

    top_3 = top_3_distinct_guests(
        guest_scores
    )

    for face in faces:

        best_guest = top_3[0]
        second_guest = top_3[1]

        score = best_guest.score
        second_score = second_guest.score

        margin = score - second_score

        if score < review_floor:
            decision = "rejected"

        elif margin < match_margin:
            decision = "review"

        elif score >= match_threshold:
            decision = "auto_confirmed"

        else:
            decision = "review"

        upsert_match(...)
```

Optimize this implementation.

Do not literally implement a Python loop over every vector if NumPy can perform the operation in bulk.

---

# 97. MATCHING WATERMARK

For normal ingestion:

```text
PhotoFaces.matched_at IS NULL
```

means:

```text
needs matching
```

After successful matching:

```text
matched_at = NOW()
```

If a threshold changes:

```text
reset matched_at
```

for the required scope.

Then run matching again.

---

# 98. MATCH RUN IDEMPOTENCY

Running the same match operation twice must not create additional Match rows.

Example:

```text
Run #1
25,000 PhotoFaces
25,000 Matches
```

Run #2:

```text
still 25,000 Matches
```

not:

```text
50,000
```

Manual decisions must remain protected.

---

# 99. GALLERY SOURCE OF TRUTH

For Week 3 compatibility:

```text
Matches
```

is the source of truth for current gallery assignments.

A confirmed gallery query is:

```text
status IN ('active', 'manually_added')
AND decision = 'auto_confirmed'
```

Manual assignment can therefore enter the gallery through:

```text
status = manually_added
```

while preserving the Match row.

---

# 100. WHAT THE AI AGENT MUST NOT DO

Do NOT:

```text
create one Match row per guest candidate
```

Do NOT:

```text
create one MatchRun per photo
```

Do NOT:

```text
query pgvector 25,000 times
```

Do NOT:

```text
load all 25,000 embeddings through SQLAlchemy ORM
```

Do NOT:

```text
overwrite manual decisions on re-run
```

Do NOT:

```text
store normalized and raw vectors together
```

Do NOT:

```text
store PNG/HEIC originals with .jpg extension
```

Do NOT:

```text
crop faces on every review request
```

Do NOT:

```text
accept file types using extension alone
```

Do NOT:

```text
return storage paths
```

Do NOT:

```text
return embeddings in API responses
```

Do NOT:

```text
implement HNSW for the 25k-face Week 2 workload
```

Do NOT:

```text
implement WhatsApp
```

Do NOT:

```text
implement public galleries
```

Do NOT:

```text
implement Week 4 perceptual deduplication
```

---

# 101. REQUIRED DOCUMENTATION

Create/update:

```text
README.md
docs/week2.md
docs/calibration.md
docs/scaling.md
```

Document:

* architecture
* worker services
* queue names
* environment variables
* upload flow
* storage layout
* face processing
* matching algorithm
* threshold logic
* multi-reference scoring
* cache strategy
* retry behavior
* manual decision protection
* performance results
* calibration results
* how to rerun matching after threshold changes
* how to scale face workers
* when HNSW should be introduced

---

# 102. FINAL ACCEPTANCE TEST

The Week 2 implementation is NOT complete until this sequence works:

```text
docker-compose up
        ↓
database migrations
        ↓
seed 500 guests
        ↓
verify 512-dim normalized reference embeddings
        ↓
create 5,000 event photos
        ↓
upload with 6 concurrent requests
        ↓
duplicate uploads tested
        ↓
Celery processes photos
        ↓
web/thumb generated
        ↓
InsightFace detects faces
        ↓
~25,000 PhotoFaces created
        ↓
low-quality faces flagged
        ↓
match_pending_faces()
        ↓
reference matrix loaded once
        ↓
NumPy matching
        ↓
Matches created
        ↓
gallery populated
        ↓
review queue populated
        ↓
organizer confirms/rejects
        ↓
new guest registers
        ↓
new guest back-match runs
        ↓
threshold changed
        ↓
unreviewed matches change
        ↓
manual decisions remain unchanged
```

---

# 103. FINAL PERFORMANCE GATE

Record actual measurements.

The final report must contain:

```text
Upload:
total time
average throughput
peak RAM

Face extraction:
total time
photos/sec
faces/sec
peak worker RAM

Matching:
reference embeddings
photo faces
total time

Gallery:
p50
p95

Failures:
failed photos
retry count
duplicate count
```

Compare against:

```text
Upload ≤45 min
Face extraction ≤30 min CPU
Matching ≤5 sec
New guest match ≤1 sec
Gallery ≤800 ms p95
```

If the target is missed:

Do not hide the failure.

Document:

```text
actual result
target
bottleneck
profiling evidence
proposed optimization
```

---

# 104. FINAL WEEK 2 CHECKLIST

## Backend

* [ ] Upload endpoint
* [ ] SHA-256 dedup
* [ ] Atomic upload flow
* [ ] Storage abstraction
* [ ] Photo state machine
* [ ] Celery
* [ ] Redis
* [ ] Beat
* [ ] Worker retry
* [ ] Face extraction
* [ ] Face crops
* [ ] Normalized bbox
* [ ] Quality flags
* [ ] Match engine
* [ ] Batched matching
* [ ] New guest back-match
* [ ] Manual match operations
* [ ] Protected decisions
* [ ] Match runs
* [ ] Pipeline status
* [ ] Media security

## Frontend

* [ ] 5,000-file uploader
* [ ] Six-file concurrency
* [ ] Virtualized upload list
* [ ] Per-file progress
* [ ] Retry
* [ ] Duplicate state
* [ ] Batch progress
* [ ] Photo grid
* [ ] Photo modal
* [ ] Guest gallery
* [ ] Review queue
* [ ] Keyboard review
* [ ] Dashboard counts

## AI

* [ ] buffalo_l
* [ ] 512-dimensional embeddings
* [ ] L2 normalization
* [ ] quality flags
* [ ] multi-reference scoring
* [ ] distinct-guest top-2
* [ ] threshold logic
* [ ] calibration

## Reliability

* [ ] worker crash recovery
* [ ] Redis restart recovery
* [ ] extraction idempotency
* [ ] duplicate upload race protection
* [ ] match idempotency
* [ ] manual decision protection
* [ ] retry limit
* [ ] stale worker recovery

## Security

* [ ] authentication
* [ ] event ownership
* [ ] media ownership
* [ ] path traversal protection
* [ ] file magic validation
* [ ] upload size limit
* [ ] image pixel limit
* [ ] no embedding leakage
* [ ] no storage-key leakage

## Performance

* [ ] 500 guests
* [ ] 5,000 photos
* [ ] ~25,000 faces
* [ ] upload benchmark
* [ ] face benchmark
* [ ] matching benchmark
* [ ] gallery benchmark

---

# 105. STOP CONDITIONS

If any of the following is discovered, stop and report before proceeding:

1. Week 1 does not actually contain Events.
2. Week 1 does not actually contain Guests.
3. Week 1 reference embeddings are missing.
4. Reference embeddings are not 512-dimensional.
5. Reference embeddings are not compatible with buffalo_l.
6. Reference embeddings are raw while Week 2 expects normalized vectors.
7. Existing authentication does not provide event ownership.
8. PostgreSQL does not have pgvector.
9. Docker cannot provide the required worker services.
10. Existing schema conflicts with the locked Week 2 schema.
11. Existing code already implements a conflicting photo/matching architecture.

Do not silently modify Week 1 architecture to hide these problems.

Report:

```text
BLOCKER
Current state:
Expected state:
Files affected:
Recommended fix:
```

Then wait.

---

# 106. CORE PRINCIPLE

The system should be:

```text
simple enough for 5,000 photos
reliable enough for real event data
fast enough for 25,000 faces
safe enough to prevent cross-user photo leakage
idempotent enough to survive worker crashes
auditable enough to explain every match
extensible enough for Week 3
```

The biggest architectural risks are NOT the matrix multiplication.

The biggest risks are:

```text
1. duplicate processing
2. incorrect Match ownership
3. overwriting manual decisions
4. raw vs normalized embeddings
5. upload deduplication races
6. insecure media access
7. per-photo matching instead of batched matching
```

Solve these correctly before optimizing anything else. add this as WEEK_2_ROADMAP.md
