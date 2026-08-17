# WEEK_4_PLAN.md

# Week 4 Build Prompt — Quality, Privacy & Production

### Phase 4 — Perceptual Dedup → Face Quality Ranking → Encrypted Biometrics → Consent & Erasure → S3 → Cloud Deployment

---

## 0. READ THIS FIRST — Three corrections to the existing docs

Before Day 22 starts, fix these. They are cheap now and expensive later.

**0.1 — Decision-number collision (documentation bug).** The Week 2 addendum locked `D17–D29`. The Week 3 prompt independently locked `D17–D30`. Two different decisions currently share the same ID (e.g. `D22` is both "bbox normalization" and "selfie search is ephemeral"). Renumber to namespaced IDs across all four docs:

```
W1.D1  – W1.D6     Week 1 locks
W2.D7  – W2.D29    Week 2 locks (original D7–D16 + addendum D17–D29)
W3.D17 – W3.D30 →  W3.D30a … renumber to W3.D1 – W3.D14
W4.D1  – W4.D22    Week 4 locks (this document)
```

This document uses `W4.Dn`. When it references an earlier lock it uses the namespaced form. Do a find-and-replace pass on the other three docs on Day 22 morning.

**0.2 — Already delivered, do NOT rebuild.** The Week 1 doc lists "multi-face detection per photo" under Week 4. Week 2 already ships it (`PhotoFaces`, N rows per photo, tested at 25 faces/photo). Strike it from Week 4 scope.

**0.3 — Amendments to earlier weeks that Week 4 forces.** These are listed in full in §9. Read that section before writing any migration — three of them change tables that Weeks 2 and 3 depend on.

---

# 1. YOUR ROLE

You are the senior engineer implementing **Week 4** on top of a working Week 1–3 codebase.

Week 4 is different in character from Weeks 1–3. Weeks 1–3 added *features*. Week 4 adds *quality, legal defensibility, and the ability to run this on the internet for a paying client without losing sleep*. Two of this week's five workstreams (encryption, erasure) are compliance-shaped: getting them 90% right is worth roughly the same as getting them 0% right, so they get full days rather than afternoons.

Same contract as before:

- Locked decisions are locked. Implement exactly.
- Anything architectural, data-correctness-affecting, security-affecting, or legally-loaded that is **not** locked below → **STOP AND FLAG. DO NOT GUESS.**
- Do not introduce technologies outside §3.
- Do not build "Beyond MVP" items (multi-organizer, payments, kiosk mode, multilingual, search-by-selfie-without-registration beyond what W3 shipped).

> [!CAUTION]
> **I am not a lawyer and this document is not legal advice.** §7 encodes a defensible engineering posture around consent and erasure. Whether it satisfies DPDP / GDPR / BIPA for your specific deployment is a question for counsel. Several open legal calls are collected in §14 — they need a human decision, not an implementation guess.

---

# 2. SCALE TARGET — UNCHANGED, WITH DERIVED WEEK 4 NUMBERS

```text
1 event
500 guests
5,000 photos (~20 GB originals)
~25,000 PhotoFaces
~50 matched photos per guest
```

Week 4 derived numbers, and the arithmetic that justifies every design choice below:

| Quantity | Value | Consequence |
|---|---|---|
| Pairwise photo comparisons for dedup | 5,000² / 2 = **12.5 M** | uint64 XOR + popcount in NumPy is **sub-second**. No LSH, no BK-tree, no index. Blocked pairwise is the correct algorithm at this scale. |
| Full 5,000×5,000 uint64 distance matrix | **200 MB** | Too big to be careless with. Block it at 1,024×1,024. |
| Faces to quality-score | 25,000 | Scored by decoding **5,000 web derivatives once** and scoring all faces in each — not by decoding 25,000 crops. ~5× fewer decodes. |
| Reference embeddings to encrypt | ~1,000 rows × 2,048 B = **2 MB** | AES-256-GCM at ~1 GB/s → **~2 ms** to decrypt the entire event's biometric reference set. Encryption cost on the matching hot path is **noise**. This is why W4.D8 is affordable. |
| Egress per fully-delivered event | 500 guests × ~200 MB = **~100 GB** | At AWS S3 egress ($0.09/GB) that is **~$9 per event, per full delivery**, before re-downloads. At Cloudflare R2 it is **$0**. This is the single largest recurring cost line in the product and it drives W4.F3. |
| ZIP cache ceiling (W3.D25) | 40 GB | On object storage this becomes a *storage* cost, not a disk-full incident. Re-derive the number after the S3 swap. |

**Do the arithmetic before you write code.** The recurring theme of Week 4 is that the *cryptography and the deduplication are cheap*, and the *egress and the erasure semantics are expensive*. Spend your care accordingly.

---

# 3. TECH STACK — ADDITIONS ONLY

Everything from Weeks 1–3 stays. New, and nothing else:

```text
Dedup / hashing:
  Pillow (already present)
  NumPy (already present)
  — implement pHash-DCT and dHash yourself (~40 lines). Do NOT add imagehash.

Quality scoring:
  OpenCV (already present)      → Laplacian sharpness, exposure histograms
  InsightFace 2d106 landmarks   → eye-openness, mouth geometry, frontality
  onnxruntime (already present) → optional FER model behind a flag (W4.D6)

Crypto:
  cryptography (AESGCM)         → envelope encryption
  boto3                         → KMS (optional, see W4.F2)

Storage:
  boto3 / botocore              → S3-compatible object storage

Deployment:
  Caddy (automatic TLS)         → reverse proxy
  Docker Compose (already present)
  Sentry SDK                    → error tracking
  prometheus-client             → /metrics endpoint
```

Explicitly forbidden this week: Kubernetes, Terraform-as-a-requirement (a documented manual runbook is acceptable), Kafka, Elasticsearch, a second database, Faiss/Milvus/Qdrant, any ML training pipeline.

---

# 4. WEEK 4 DEFINITION OF DONE

- [ ] Every photo has a 64-bit pHash and dHash computed at ingest; existing 5,000 photos backfilled
- [ ] Near-duplicate photos are grouped into clusters; **no photo is ever auto-deleted**
- [ ] Every face has sharpness, eye-openness, smile, frontality, exposure sub-scores and a composite quality score
- [ ] "Best photo" is selected **per (guest, cluster)** — not globally per cluster — and drives the default gallery view
- [ ] Guest gallery defaults to best-of-burst with a "show all N similar" expander; ZIP defaults to all, with `best_only` option
- [ ] Guest reference embeddings are encrypted at rest with per-guest DEKs; plaintext `vector(512)` column dropped
- [ ] Deleting a guest's wrapped DEK provably renders their biometric reference data unrecoverable (crypto-shredding), and there is a test that proves it
- [ ] Matching still meets the Week 2 budget (≤ 5 s full event, ≤ 1 s new guest) **with decryption in the path**
- [ ] Versioned consent is recorded with policy version, purpose, timestamp, method; Week 1's `consent_given_at` backfilled
- [ ] Guest can, from their magic link and with no login: see exactly what is stored about them, export it as JSON, and request erasure
- [ ] Erasure runs end-to-end in ≤ 60 s: guest row, reference images, embeddings, DEK, tokens, matches, ZIPs, notification logs, face crops, and redaction of their `PhotoFaces` embeddings — with an immutable audit record and a deletion certificate
- [ ] Event-level retention purge job runs on schedule and is dry-runnable
- [ ] `S3Storage` implements `StorageBackend`; **zero** `open()` calls outside the storage layer (enforced by a lint test)
- [ ] 20 GB migrated local → object storage, checksum-verified, resumable, with per-object tier routing and zero downtime
- [ ] Public and organizer media serve via short-TTL presigned URLs, authorization still enforced by our API
- [ ] Full stack deployed to a real host over HTTPS with a real domain, automated backups, and a tested restore
- [ ] Structured JSON logs, `/metrics`, Sentry, and uptime checks live
- [ ] `docs/dedup.md`, `docs/quality.md`, `docs/crypto.md`, `docs/privacy.md` (updated), `docs/deployment.md`, `docs/runbook.md` (updated), `docs/costs.md` written
- [ ] Full scale run on the deployed environment inside the budget in §5, with a DR drill (restore from backup) completed and timed

---

# 5. PERFORMANCE & COST BUDGET (this is the spec)

| Stage | Volume | Target | Notes |
|---|---|---|---|
| pHash + dHash, inline | 1 photo | ≤ 25 ms | Folded into `extract_faces`, computed from the web derivative already in memory. Zero extra decodes. |
| pHash backfill | 5,000 photos | ≤ 6 min | 4 workers, decodes web derivatives |
| Dedup clustering | 12.5 M pairs | ≤ 3 s | Blocked NumPy popcount + union-find |
| Quality scoring, inline | 1 face | ≤ 15 ms | Landmarks already computed by detection — reuse, do not re-detect |
| Quality backfill | 25,000 faces / 5,000 decodes | ≤ 8 min | 4 workers, batch by photo |
| Best-of-burst ranking | 25,000 matches | ≤ 5 s | Pure SQL + NumPy, no image I/O |
| Reference decrypt (full event) | ~1,000 embeddings | ≤ 50 ms | 1 KMS unwrap per event, then local AES |
| Full-event match **with crypto** | 25k × 500 | ≤ 5 s | Unchanged from W2 — prove it |
| New-guest back-match **with crypto** | 1 × 25k | ≤ 1 s | Unchanged from W2 — prove it |
| Guest data export | 1 guest | ≤ 2 s | JSON, no media inlined |
| Guest erasure, end-to-end | 1 guest, ~50 matches | ≤ 60 s | Includes object-storage deletes |
| Event retention purge | 1 event, 20 GB | ≤ 20 min | Batched deletes, resumable |
| Storage migration local→S3 | 20 GB / ~15,000 objects | ≤ 60 min | 8 parallel uploads, checksum-verified |
| Presigned URL issue | 1 | ≤ 15 ms | Signed locally, **no** network call to the provider |
| Public thumb via CDN/presigned | — | ≤ 120 ms p95 | Unchanged from W3.D-media |
| Backup + verified restore drill | full DB + 20 GB | ≤ 45 min | Timed once, written down |

---

# 6. [DECISION] Week 4 locks — W4.D1 … W4.D22

## 6.1 Deduplication

**W4.D1 — Two hashes, both 64-bit, both `BIGINT`.** Compute pHash-DCT (32×32 grayscale → DCT-II → top-left 8×8 excluding DC → median threshold) as the primary, and dHash (9×8 grayscale → horizontal gradient) as a corroborating signal. Store as signed `BIGINT` (Postgres has no unsigned; cast through `int64`, document the wraparound). Hamming distance in SQL is `bit_count(a # b)` (Postgres 14+); in NumPy it is a `uint8` popcount lookup table over the XOR'd bytes.

*Rationale for two:* pHash is robust to resize/compression/mild colour shifts but occasionally collapses low-detail images (dark dance-floor shots — you will have hundreds); dHash is robust to brightness but sensitive to crop. Requiring agreement kills the dominant false-positive mode at essentially zero cost.

**W4.D2 — Near-duplicate predicate.** Two photos in the same event are near-duplicates iff:

```text
hamming(phash) <= 6
AND hamming(dhash) <= 12
AND (
      exif_taken_at IS NULL ON EITHER SIDE
   OR abs(taken_at_a - taken_at_b) <= 30 seconds
)
```

The temporal guard is not optional. A ceremony backdrop photographed at 14:02 and again at 17:40 can be within 6 bits of each other and is emphatically not a burst. All three thresholds live in config (`DEDUP_PHASH_MAX`, `DEDUP_DHASH_MAX`, `DEDUP_TIME_WINDOW_S`) and are re-tuned on real data on Day 28.

**W4.D3 — Clustering is union-find over the pair set, per event.** Transitive: A~B, B~C ⇒ one cluster {A,B,C} even if A≁C. Bursts drift. Cluster IDs are stable across re-runs when membership is unchanged (key the cluster on `sha256(sorted(photo_ids))` and reuse the row on match). Blocked comparison at 1,024×1,024 to keep peak memory under ~10 MB.

**W4.D4 — Dedup NEVER deletes. It groups.** No photo row is deleted, no file is unlinked, no match is removed by the dedup pipeline. Output is `Photos.dup_cluster_id` + `PhotoClusters`. Removal is always an explicit, per-photo, organizer-initiated action through the existing `DELETE /photos/{id}`. Write this in the code comment at the top of the task, because someone will eventually be tempted.

*Rationale:* a false-positive cluster costs a collapsed thumbnail. A false-positive delete costs a photograph that does not exist anymore. The asymmetry is total.

**W4.D5 — Cluster representative ≠ guest's best photo.** `PhotoClusters.representative_photo_id` is the globally best photo of the burst (highest mean face quality, tiebreak on face count then sharpness) and is used only in the **organizer's** photo grid. The **guest's** gallery uses `Matches.cluster_rank`, computed per (guest, cluster), because in frame 2 of a five-shot burst Guest A blinked and Guest B finally smiled. Collapsing a burst to one global winner silently hands half your guests their worst photo.

## 6.2 Quality scoring

**W4.D6 — Five sub-scores, all in `[0,1]`, all stored, plus a composite.**

| Sub-score | Method | Notes |
|---|---|---|
| `sharpness_score` | Laplacian variance over the face bbox region **of the web derivative**, normalized by bbox pixel area, then squashed with a logistic whose midpoint is calibrated on Day 28 | Measured at a consistent resolution — never on the 256 px crop, never on the original. Blur is resolution-dependent and mixing sources makes the number meaningless. |
| `eye_open_score` | Eye Aspect Ratio from InsightFace 2d106 landmarks, min of both eyes | Landmarks come free from detection — **reuse them, do not re-run the detector** |
| `smile_score` | Mouth Aspect Ratio + mouth-corner elevation relative to the inter-ocular baseline, from 2d106 | Geometric v1. See below. |
| `frontality_score` | From existing `yaw`/`pitch`/`roll`: `cos(yaw)·cos(pitch)`, clamped | Already stored by Week 2 |
| `exposure_score` | Penalty for clipped highlights/shadows in the face region histogram | Catches backlit and flash-blown faces |

Composite:

```text
composite_quality =
    0.30 * sharpness
  + 0.25 * eye_open
  + 0.20 * frontality
  + 0.15 * exposure
  + 0.10 * smile
```

Weights live in config and are recorded per row as `scoring_model_version` so a re-weighting is auditable and replayable, exactly like `threshold_used` in Week 2.

*On smile:* the geometric MAR approach is a genuinely mediocre smile detector. It is shipped as v1 because it costs zero additional model weight, zero additional inference, and it is only 10% of the composite. Swapping in an ONNX FER model (HSEmotion-style) behind `SMILE_MODEL=geometric|onnx` is a Week 5 line item, not a Week 4 one. Do not train anything.

**W4.D7 — Quality is a ranking signal, never a gate.** This extends W2.D14. Low-quality faces stay matchable if they were matchable. Quality changes *ordering* and *default visibility*, never *membership*. A blurry photo of you is still a photo of you and you may well want it.

## 6.3 Encryption of biometric data

**W4.D8 — Three-tier envelope encryption, and only the reference embeddings are encrypted.**

```text
MASTER KEY  (KMS, or age/env key — see W4.F2)
    │  unwraps once per process, cached in memory
    ▼
EVENT KEK   (Events.wrapped_kek, bytea)
    │  unwraps once per event, cached in memory with TTL
    ▼
GUEST DEK   (Guests.wrapped_dek, bytea)
    │  local AES unwrap, ~microseconds
    ▼
FaceEmbeddings.embedding_enc  (AES-256-GCM ciphertext + 96-bit nonce)
```

`FaceEmbeddings.embedding vector(512)` is **dropped** after backfill. `PhotoFaces.embedding vector(512)` stays plaintext in the database.

*Rationale, because this asymmetry will be questioned:* guest reference embeddings are directly joined to a name, a phone number, and a face photo — that is identified biometric data and it is the crown jewel of a database dump. There are ~1,000 of them and they are already loaded exactly once per match run into a cached matrix, so decryption costs ~2 ms and lands nowhere near a hot path. `PhotoFaces` embeddings are 25,000 rows of *unidentified* face vectors, they are the working set of the matching engine, and encrypting them would (a) destroy the pgvector ad-hoc candidates path from W2.§57 and (b) put a decrypt in front of every chunked cursor read. They are protected by volume-level encryption at rest (W4.D11) instead. This is a deliberate, documented tradeoff — write it in `docs/crypto.md`, do not leave it as folklore.

**W4.D9 — AAD binds ciphertext to its row.** AES-GCM additional authenticated data is `f"{guest_id}:{face_embedding_id}:{model_version}"`. An attacker with write access cannot swap Guest A's ciphertext into Guest B's row without the decrypt failing loudly. Nonce is 96-bit random per encryption, stored as a prefix on the ciphertext blob. Never reuse a nonce.

**W4.D10 — Crypto-shredding is the erasure primitive.** Destroying `Guests.wrapped_dek` renders every reference embedding for that guest permanently unrecoverable, including in every backup taken before the deletion. Destroying `Events.wrapped_kek` does the same for an entire event. This is why erasure (§Day 25) is scheduled *after* encryption (§Day 24) — the deletion story depends on it. Deletion still also removes the rows; crypto-shredding is defence in depth and, crucially, is the only mechanism that reaches into historical backups.

**W4.D11 — The master key never lives in a database backup.** Volume/disk encryption is enabled on the database host or managed instance. The master key lives in KMS or in an environment secret injected at runtime, and the backup pipeline is explicitly tested against a restore *without* the master key present, to confirm that the restored biometrics are inert. This test is part of the Day 28 DR drill.

**W4.D12 — [AMENDS W2.§55] The reference matrix cache moves out of Redis.** Week 2 cached the decrypted reference matrix in Redis keyed by fingerprint. Caching plaintext biometrics in an unauthenticated, unencrypted, frequently-exposed-to-the-internet Redis instance defeats W4.D8 entirely. The reference matrix is 2 MB. Cache it in **process memory only** — a small LRU keyed by `(event_id, fingerprint)`, max 8 events, TTL 10 min. Redis keeps the *fingerprint* (cheap invalidation signal), never the vectors. Same rule applies to the W3.D22 selfie-search face matrix: process memory, not Redis.

## 6.4 Consent, export, erasure

**W4.D13 — Consent is versioned, purpose-scoped, and append-only.** `ConsentRecords` rows are never updated or deleted, only superseded. Each row: `policy_version`, `purpose` (enum: `face_matching`, `photo_delivery`, `marketing`), `granted` (bool), `method` (`registration_form`, `portal`, `organizer_attested`, `selfie_search_checkbox`), `ip_hash`, `user_agent_hash`, `created_at`. Week 1's `Guests.consent_given_at` is backfilled into a `policy_version='v0-legacy'` row and the column is kept for compatibility but marked deprecated in the model docstring.

**W4.D14 — Erasure is guest-initiated, token-authenticated, organizer-visible, and grace-delayed.** Flow:

```text
guest clicks "Delete my data" on /g/{code}
        ↓
confirmation screen states exactly what disappears and what does not
        ↓
ErasureRequests row: status=pending, purge_after = now + 7 days
        ↓
guest's magic link is revoked IMMEDIATELY (access stops at request time)
        ↓
organizer sees it in a queue; may expedite; may NOT deny (see W4.F5)
        ↓
beat job executes purge after grace period
        ↓
AuditLog row + deletion certificate (JSON, signed hash) retained
```

The 7-day grace exists for accidental clicks and for the "my cousin used my phone" case, not to give the organizer a veto. Access is cut immediately so the grace period is not itself a privacy exposure.

**W4.D15 — What erasure destroys, and what it deliberately does not.**

Destroyed: `Guests` row (hard delete after grace), reference image objects, `FaceEmbeddings` rows, `Guests.wrapped_dek` (crypto-shred), `GuestAccessTokens`, `Matches`, `NotificationLogs` content (retain a tombstone: guest_id-hash, channel, timestamp, for legal proof-of-send), `ZipArchives` rows **and their objects**, `ConsentRecords` (retain a tombstone with policy version + timestamps, no PII).

Also destroyed — and this one is easy to miss: for every `PhotoFace` that had an `active` or `manually_added` match to this guest, set `embedding = NULL`, delete `crop_key` object, set `is_matchable = false`, `erasure_redacted = true`. Their face vector is their biometric data whether or not it sits in the guest table, and leaving it means they get silently re-matched the next time someone re-runs matching.

**Not destroyed:** the photographs themselves, and other guests' matches to them. The photograph is the photographer's work and other data subjects appear in it. Whether an erasure request must also remove the underlying image is a policy and legal question — **flagged in W4.F5**, with a config switch (`ERASURE_DELETES_PHOTOS=false` default) so the answer can be changed without a code change.

**W4.D16 — Export before erasure, always offered.** The confirmation screen offers a one-click JSON export first. Export contains: profile fields, consent history, event, match list with photo IDs and thumbnail URLs (valid 24 h), notification history, and a manifest. It contains **no embeddings, no vectors, no similarity scores, no storage keys** — the W3.D30 public serializer rules apply unchanged.

**W4.D17 — Retention purge is per-event, scheduled, and dry-runnable.** `Events.retention_days` (default 365, from `DEFAULT_RETENTION_DAYS`), `Events.retention_purge_at = event.date + retention_days`. A daily beat job purges eligible events. `POST /events/{id}/retention/dry-run` returns exactly what would be destroyed and how many bytes, and must be run and eyeballed before any real purge. Organizer receives a warning notification 14 days before.

## 6.5 Object storage and delivery

**W4.D18 — Per-object storage tier, not a big-bang cutover.** `Photos.storage_tier` enum `local | s3`, default `local`. Migration copies → verifies checksum → flips the column → optionally unlinks local. Reads route on the column. This makes a 20 GB / 15,000-object migration resumable, interruptible, and rollback-able, and it means a failed migration is a partial migration rather than an outage. Guest reference images and ZIP archives get the same treatment via their own tier columns.

**W4.D19 — Authorization stays in our API; bytes move to presigned URLs.** The media endpoints from W2/W3 keep doing the full ownership + visibility check, then return **`302` to a presigned URL with TTL 300 s** instead of streaming bytes, when `storage_tier = s3`. Presigning is a local HMAC operation — no network round trip to the provider. `Content-Disposition` and `Content-Type` are pinned via response-header overrides in the signature so the client cannot influence them.

*The tradeoff, stated plainly:* a presigned URL is bearer-capable for 300 s and can be copy-pasted. That is a strictly smaller exposure than the 90-day magic link already accepted in W3.D19, and it removes the entire 20 GB of egress from the Python process. Thumbnails may additionally sit behind a CDN with a longer TTL — but only if W4.F3 resolves to a provider with a CDN, and only with `private` cache semantics. Keep the streaming path alive behind `STORAGE_DELIVERY=proxy|presigned` for local dev and for any client that breaks on redirects.

**W4.D20 — The lint test is part of the deliverable.** A test that greps the backend for `open(`, `os.path.join(STORAGE_ROOT`, `shutil.copy`, and `Path(...).write_bytes` outside `services/storage/` and fails the build on a hit. Week 2 declared this rule; Week 4 is when it actually gets enforced, because Week 4 is when violating it breaks production.

**W4.D21 — ZIPs are built to object storage via multipart upload, streamed, never fully staged when avoidable.** Above `ZIP_MULTIPART_THRESHOLD_MB=100`, use S3 multipart with 16 MB parts written as the archive is produced. Below it, temp file then single PUT. `ZIP_STORED` stays locked (W3.D25) — the arithmetic has not changed. The 40 GB disk watermark guard becomes a *storage quota* guard: still enforced, now measured against a configured budget rather than `df`.

## 6.6 Deployment

**W4.D22 — Single-VM Compose, managed data services, Caddy for TLS. Kubernetes is out.**

```text
        Internet
           │  443, TLS via Caddy (automatic ACME)
           ▼
      ┌─────────┐
      │  Caddy  │──► frontend (Next.js)
      └────┬────┘──► backend (FastAPI, N replicas behind Caddy round-robin)
           │
   ┌───────┴────────────────────────────────┐
   │                                        │
Managed Postgres 16 + pgvector        Managed Redis
   │                                        │
   └──────────► workers: faces ×4, match ×1, maintenance ×1, beat ×1
                                            │
                                     Object storage (S3-compatible)
```

Rules that are not negotiable:

- **Migrations run as a one-shot job**, never on application startup. Four backend replicas racing `alembic upgrade head` is a corrupted schema.
- Every service declares a `healthcheck`; Caddy only routes to healthy backends.
- Secrets come from an env file with `600` perms or the platform's secret store — never baked into an image, never committed, never in `docker-compose.yml` literals.
- Face workers get a memory limit reflecting the ~500 MB RSS/worker figure from W2.§30. 4 workers on a box with less than 6 GB total is a documented misconfiguration and the compose file should say so in a comment.
- Postgres must have `pgvector` available. Verify this on the *specific* managed provider before Day 27 — it is a `CREATE EXTENSION` privilege question and providers differ.
- Backups: nightly logical dump + provider PITR, retained 30 days, stored in a **different** account/bucket from the primary, master key **excluded**.
- GPU is optional and off by default. Document the one-line change (`USE_GPU=true`, GPU base image, 1 worker with full cores) and the cost per event so it can be turned on for a large job and off again.

---

# 7. DATA MODEL — WEEK 4 ADDITIONS

```text
PhotoClusters          ConsentRecords         ErasureRequests        DataExports           AuditLog
-------------          --------------         ---------------        -----------          --------
id                     id                     id                     id                   id
event_id (FK csc)      guest_id (FK csc)      guest_id (FK)          guest_id (FK csc)    actor_type (enum)
membership_hash        event_id (FK denorm)   event_id (FK denorm)   event_id (FK denorm) actor_id (null)
size                   policy_version         requested_via (enum)   storage_key          action (enum)
representative_        purpose (enum)         reason (null)          storage_tier         object_type
  photo_id (FK)        granted (bool)         status (enum)          bytes                object_id
method                 method (enum)          purge_after            expires_at           event_id (null)
params (jsonb)         ip_hash                grace_days             created_at           payload (jsonb)
mean_quality           user_agent_hash        executed_at            downloaded_at        ip_hash
time_span_s            superseded_by (null)   certificate_hash                            created_at
created_at             created_at             error                                       (append-only,
updated_at                                    created_at                                   no UPDATE/DELETE
                                              updated_at                                   grant)
```

**Amendments to existing tables**

```text
Photos          + phash BIGINT NULL
                + dhash BIGINT NULL
                + hash_computed_at
                + dup_cluster_id (FK PhotoClusters, null, ON DELETE SET NULL)
                + is_cluster_representative bool default false
                + storage_tier enum('local','s3') default 'local'

PhotoFaces      + sharpness_score, eye_open_score, smile_score,
                  frontality_score, exposure_score, composite_quality  (all float null)
                + scoring_model_version text null
                + scored_at timestamptz null
                + erasure_redacted bool default false

Matches         + cluster_rank int null        -- 1 = this guest's best photo in that cluster
                + ranked_at timestamptz null

Guests          + wrapped_dek bytea null
                + dek_key_id text null
                + deleted_at timestamptz null
                + purge_after timestamptz null

Events          + wrapped_kek bytea null
                + kek_key_id text null
                + retention_days int default 365
                + retention_purge_at timestamptz null
                + dedup_enabled bool default true
                + quality_ranking_enabled bool default true

FaceEmbeddings  + embedding_enc bytea null
                + enc_nonce bytea null
                + enc_key_id text null
                - embedding vector(512)        -- DROPPED after verified backfill, Day 24

ZipArchives     + storage_tier enum('local','s3') default 'local'
                + best_only bool default false
```

**Indexes**

```text
Photos:          INDEX(event_id, dup_cluster_id)
                 INDEX(event_id, hash_computed_at)      -- backfill scan
                 INDEX(event_id, storage_tier)          -- migration scan
PhotoFaces:      INDEX(event_id, scored_at)             -- backfill scan
                 INDEX(photo_id, composite_quality DESC)
Matches:         INDEX(guest_id, status, cluster_rank, similarity DESC)   -- REPLACES the W2 gallery index
PhotoClusters:   UNIQUE(event_id, membership_hash)
ConsentRecords:  INDEX(guest_id, purpose, created_at DESC)
ErasureRequests: INDEX(status, purge_after)
AuditLog:        INDEX(object_type, object_id, created_at DESC)
                 INDEX(event_id, created_at DESC)
```

**Cascade rules — verify all of these in tests**

```text
Delete photo   → PhotoFaces, Matches cascade (W2, unchanged)
               → cluster membership_hash becomes stale; cluster is re-derived, not orphaned
Delete cluster → Photos.dup_cluster_id SET NULL (never cascade-delete photos)
Delete guest   → Matches, tokens, ZIPs, DataExports cascade
               → ConsentRecords cascade to tombstone rows
               → PhotoFaces SURVIVE but are redacted per W4.D15
               → AuditLog rows SURVIVE (append-only, guest_id replaced by a salted hash)
Delete event   → everything cascades except AuditLog tombstones
```

---

# 8. DAY-BY-DAY PLAN

### Day 22 — Perceptual dedup

**Today's task**

- Migration: `PhotoClusters`, `Photos` hash/cluster/tier columns, indexes.
- `services/hashing.py`: `phash_dct(pil_image) -> int64`, `dhash(pil_image) -> int64`, `hamming(a, b)`. Pure functions, unit-tested against hand-computed fixtures and against a set of known transformations (resize 50%, JPEG q60, ±10% brightness, 1° rotation) which must all stay within threshold, and against genuinely different photos which must not.
- **[AMENDS W2]** Hook hash computation into `extract_faces` — computed from the web derivative already decoded in memory, before detection. New photos never need a backfill.
- Backfill task `backfill_hashes(event_id)`, chunked, resumable, idempotent (`WHERE hash_computed_at IS NULL`).
- `cluster_duplicates(event_id)` task: load all `(id, phash, dhash, taken_at)` for the event → blocked NumPy popcount → apply W4.D2 predicate → union-find → upsert `PhotoClusters` keyed on `membership_hash` → set `Photos.dup_cluster_id`. Wrapped in the same Redis event lock pattern as Week 2's matching (`event:{id}:dedup_lock`).
- `POST /events/{id}/dedup-runs`, `GET /events/{id}/clusters`, `GET /clusters/{id}`.
- Organizer UI: photo grid gains a "group duplicates" toggle. On, the grid shows one tile per cluster with a `×N` badge; clicking expands the burst inline. A "review clusters" view shows suspicious clusters (size ≥ 8, or time span > 20 s) for eyeballing, with a per-cluster "not duplicates" action that writes an exclusion so re-runs respect it.

**Done when:** the seeded 5,000-photo event clusters in ≤ 3 s, a hand-inspected sample of 20 clusters contains zero false groupings, and re-running produces byte-identical cluster IDs.

---

### Day 23 — Face quality scoring + best-of-burst ranking

**Today's task**

- Migration: `PhotoFaces` score columns, `Matches.cluster_rank`, the replacement gallery index.
- `services/face_quality.py`: the five sub-scores from W4.D6 as pure functions taking `(web_image_array, bbox_px, landmarks_2d106)`. Unit-tested with synthetic cases (Gaussian-blurred face → low sharpness; closed-eye fixture → low eye_open; profile shot → low frontality).
- **[AMENDS W2]** Hook scoring into `extract_faces`, **reusing the landmarks the detector already produced**. If your Week 2 code discards landmarks, that is the bug to fix today — re-running detection to get them back costs a second full pass over 5,000 images.
- Backfill task `backfill_quality(event_id)`: iterate **photos**, decode the web derivative once, score all its faces, single bulk update per photo. Not one task per face.
- `rank_guest_clusters(event_id)`: for each `(guest_id, dup_cluster_id)` over visible matches, assign `cluster_rank` by `composite_quality` of *that guest's* face in each photo, tiebreak on `similarity`, then on `photo_id` for determinism. Chain after dedup and after any match run. Photos with no cluster get `cluster_rank = 1`.
- `POST /events/{id}/quality-runs` (rescore with a new weight vector, bumps `scoring_model_version`).
- Gallery integration: guest portal and organizer guest-gallery default to `cluster_rank = 1`; each tile with a cluster shows "+N similar" which expands in place. `GET /public/guest/{code}/photos?show_all=true` returns the flat list.
- **[AMENDS W3]** ZIP gains `best_only` (default `false` — a guest asking for "all my photos" means all). `match_set_hash` must incorporate the `best_only` flag or you will serve a cached full ZIP to a best-only request.
- Organizer UI: quality score badge on the photo-detail face overlay, and a "lowest quality faces" filter — useful for spotting a mis-focused lens across a whole batch.

**Done when:** in a five-shot burst where a guest blinks in three frames, that guest's gallery shows a frame where their eyes are open, and a *different* guest in the same burst gets a different frame.

---

### Day 24 — Encrypted biometrics + key management

**Today's task**

- `services/crypto/`: `KeyProvider` interface with `LocalKeyProvider` (master key from env, for dev) and `KmsKeyProvider` (AWS KMS, for prod) — resolved by `KMS_PROVIDER`. `envelope.py`: `wrap/unwrap` for KEKs and DEKs, `encrypt_embedding/decrypt_embedding` with AAD per W4.D9. In-process key cache with TTL and an explicit `purge_key_cache()` used by tests.
- Migration: `Events.wrapped_kek`, `Guests.wrapped_dek`, `FaceEmbeddings.embedding_enc/enc_nonce/enc_key_id` (nullable).
- `scripts/backfill_encrypt_embeddings.py`: per event → generate KEK → per guest → generate DEK → encrypt each reference embedding → **verify decrypt round-trip and bitwise equality against the plaintext column before committing** → commit. Resumable, dry-runnable, reports counts.
- **Only after** a verification script confirms 100% coverage and round-trip equality across the whole database: a second migration drops `FaceEmbeddings.embedding`. Two separate migrations, two separate deploys' worth of confidence. Never one.
- **[AMENDS W2.§55 / W4.D12]** Rip out the Redis reference-matrix cache. Replace with an in-process LRU. Redis retains only the fingerprint for invalidation. Do the same for W3's selfie matrix.
- **[AMENDS W2]** `MatchingService.load_reference_matrix` now decrypts. The assertions from W2.§56 (512-dim, finite, ‖v‖≈1) run *after* decryption and must fail loudly. `scripts/verify_embeddings.py` updated to work on ciphertext.
- Crypto-shred test — this is the headline deliverable, not a nice-to-have: encrypt a guest → snapshot the ciphertext rows → delete `wrapped_dek` → assert that decryption raises and that no code path anywhere recovers the vector → assert the same holds against a restored copy of a backup taken *before* the shred.
- **Re-run the Week 2 performance gate.** Full-event match must still be ≤ 5 s and new-guest back-match ≤ 1 s, now with decryption in the path. Record both numbers in `docs/crypto.md` next to the pre-encryption numbers.
- `docs/crypto.md`: key hierarchy diagram, rotation procedure, what is and is not encrypted **and why** (W4.D8's rationale, in full), the backup/key-separation rule, and the crypto-shred guarantee stated precisely.

**Done when:** the plaintext column is gone, matching is inside budget, and the shred test passes against a restored backup.

---

### Day 25 — Consent, data export, erasure

**Today's task**

- Migration: `ConsentRecords`, `ErasureRequests`, `DataExports`, `AuditLog` (with a DB-level guard: revoke UPDATE/DELETE on `AuditLog` from the application role — append-only enforced by the database, not by good intentions).
- Backfill Week 1 `consent_given_at` → `ConsentRecords(policy_version='v0-legacy', purpose='face_matching', method='registration_form')`.
- Consent capture at the three real points: guest registration form (Week 1), selfie-search checkbox (Week 3), and portal re-consent if `policy_version` has advanced. Policy text versioned in `docs/policy/` and served from an endpoint so the recorded version is provably the text the guest saw.
- `GET /api/v1/public/guest/{code}/data` → the "what we know about you" page: profile, consent history, event, photo count, notification history. Plain language, no jargon, no internal IDs.
- `POST /api/v1/public/guest/{code}/export` → Celery job → `DataExports` row → download link, TTL 24 h, W3.D30 serializer rules enforced by the same test.
- `POST /api/v1/public/guest/{code}/erasure-request` → confirmation flow per W4.D14: a screen stating exactly what is destroyed and what is retained (the photographs, and why), an offer to export first, then a typed confirmation. Immediate token revocation on submit. Rate-limited (2/hour/token).
- `execute_erasure(request_id)` task implementing W4.D15 in a single transaction for the DB portion, followed by storage deletes, followed by the audit record and certificate (`sha256` over a canonical JSON of what was destroyed, timestamped). Storage deletes are retried and reconciled by a beat sweep — an orphaned object must not block or fail the erasure.
- Beat: `process_pending_erasures` (hourly), `purge_expired_events` (daily, per W4.D17), `sweep_orphaned_objects` (daily).
- Organizer UI: erasure queue with countdowns, expedite action, completed-with-certificate history. Event settings gains retention days + a dry-run purge preview showing objects and bytes.
- `docs/privacy.md` rewritten: every data category, where it lives, how long, lawful basis placeholder, retention windows, the erasure matrix (destroyed / redacted / retained, with the reason for each), and the crypto-shred guarantee.

**Done when:** a guest erasure completes in ≤ 60 s, a subsequent full match re-run does **not** resurrect them anywhere, and a grep of the database for their phone number returns zero rows.

---

### Day 26 — S3 storage backend + migration + presigned delivery

**Today's task**

- `services/storage/s3.py` implementing `StorageBackend`, plus `signed_url(key, ttl, disposition, content_type)`. Configured by endpoint URL so any S3-compatible provider works (this is what keeps W4.F3 a config decision rather than a code decision).
- The W4.D20 lint test. Fix every violation it finds. There will be violations.
- Migration: `storage_tier` columns on `Photos`, `Guests` (reference image), `ZipArchives`.
- `scripts/migrate_storage.py`: resumable, `--dry-run`, `--event-id`, `--concurrency`, per-object flow = read local → PUT → GET-back or compare ETag/checksum → flip tier → optionally unlink. Progress, throughput, and ETA to stdout. Interrupting it mid-run and restarting must be a no-op for already-migrated objects.
- Reads route on tier everywhere. New writes go to `STORAGE_BACKEND`. Dual-read stays supported indefinitely — it costs one branch and it is what makes the migration safe.
- **[AMENDS W2 + W3]** All media endpoints: authorization unchanged, then `302` to a presigned URL when tier is `s3`, per W4.D19. `STORAGE_DELIVERY=proxy` preserves the old behaviour for dev. Verify Week 3's negative-authorization suite still passes — every one of those tests must still return 403/404 *before* any URL is signed.
- **[AMENDS W3]** ZIP builder writes via multipart per W4.D21; the disk-watermark guard becomes a storage-quota guard.
- Lifecycle rules documented and applied: ZIP prefix expires at 48 h server-side (belt and braces alongside the beat sweep); no public-read ACLs anywhere; bucket public access blocked; versioning on for originals (a bad `DELETE` should be recoverable) and off for derivatives.
- `docs/costs.md`: the ~100 GB/event egress arithmetic, storage cost at 20 GB/event, ZIP cache cost, and a per-event total under each provider option in W4.F3.

**Done when:** 20 GB migrates in ≤ 60 min with checksum verification, the app serves entirely from object storage with the local files renamed away, and nothing breaks.

---

### Day 27 — Cloud deployment, TLS, backups, observability

**Today's task**

- `docker-compose.prod.yml` per W4.D22: Caddy, frontend, backend ×2, worker-faces ×4, worker-match, worker-maintenance, beat, one-shot migration job. Flower **not** exposed publicly — bound to localhost, reached over SSH tunnel, documented in the runbook.
- Managed Postgres + Redis provisioned; `CREATE EXTENSION vector` verified on the actual provider; connection pooling sized (`pool_size` × replica count must stay under the provider's connection cap — do this arithmetic, it is the most common way a small deploy falls over).
- Postgres tuning applied and recorded: `work_mem=64MB`, `maintenance_work_mem=512MB`, `shared_buffers` at ~25% of the instance's RAM (the actual instance, not a guess).
- Domain, DNS, Caddy automatic TLS, HSTS, security headers from W3 re-verified in production. HTTP→HTTPS redirect.
- Structured JSON logging with request IDs propagated into Celery tasks; log levels by env; **assert no token plaintext, no phone numbers, no storage keys, and no vectors in logs** — automated, not eyeballed.
- Sentry for backend, workers, and frontend with release tagging and PII scrubbing configured. `/metrics` (prometheus-client) exposing queue depths, task durations, photos processed, match run durations, error counts. An external uptime check on `/health` and on the public portal route.
- Backups: nightly `pg_dump` to a separate bucket/account, 30-day retention, PITR on if the provider offers it, master key excluded per W4.D11. Object storage versioning on originals.
- Deploy runbook: build, push, migrate (one-shot), rolling restart, rollback, and a "worker is wedged" recovery procedure.
- Worker scaling formula documented: `face_workers = min(vCPU, floor((RAM_GB - 2) / 0.6))`, with the GPU alternative and its cost noted.

**Done when:** a fresh clone deploys to the real host from the runbook with no undocumented steps, the public portal loads over HTTPS on a phone on cellular, and a restore from last night's backup succeeds on a scratch database.

---

### Day 28 — Full-scale validation, security & privacy audit, docs, DR drill

**Today's task**

- **Threshold re-tuning on real data.** Re-run the Week 2 calibration sweep, and additionally tune the three dedup thresholds (W4.D2) against a hand-labelled set of ≥ 100 photo pairs (≥ 50 true bursts, ≥ 50 hard negatives: same backdrop different time, same outfit different pose, two photos of the same static object). Report cluster precision/recall. Bias toward **precision** again — an over-merged cluster hides a photo from a guest, and hidden photos generate support tickets you cannot debug.
- **Quality-weight sanity check.** Take 50 bursts, have a human pick the best frame per person, compare against `cluster_rank = 1`. Report top-1 agreement. If it is below ~60%, the weights are wrong — retune, do not ship and hope. Write the number in `docs/quality.md` even if it is unflattering.
- **Full-scale run on the deployed environment**, cold: seed → upload 5,000 → extract → hash → cluster → score → match → rank → 500 magic links → 50 portal loads → 20 ZIPs → 5 erasures. Every stage timed against §5. Peak RSS per worker recorded.
- **Security audit pass:** re-run the entire Week 3 negative suite against production URLs; presigned-URL TTL expiry verified; presigned URL for Organizer B's photo not obtainable by Organizer A at any point in the flow; path traversal on storage keys; the `"embedding"`/phone/storage-key grep across *all* responses including the new export and consent endpoints; rate limits verified live; secrets not present in any image layer (`docker history` + a layer grep).
- **Privacy audit pass:** erasure completeness verified by a scripted grep across DB, object storage, Redis, and logs for a test guest's identifiers; consent records present for every guest; retention dry-run output reviewed; audit log append-only-ness verified by attempting an UPDATE as the app role and confirming it is denied.
- **DR drill, timed and written down:** destroy the app host, restore DB from backup, redeploy from the runbook, verify data integrity, verify that biometrics restored *without* the master key are inert. Record wall-clock RTO and the actual RPO.
- Docs finalized: `docs/dedup.md`, `docs/quality.md`, `docs/crypto.md`, `docs/privacy.md`, `docs/deployment.md`, `docs/costs.md`, `docs/runbook.md`, and a `README` Week 4 section. Runbook must cover: revoke a leaked link, re-run dedup/quality after a threshold change, rotate the master key, execute an urgent erasure, storage quota exceeded, worker wedged, restore from backup, roll back a deploy.

**Done when:** every number in §5 has a measured counterpart in `docs/perf-week4.md`, every miss has a documented bottleneck and a proposed fix, and the DR drill has a recorded RTO.

---

# 9. AMENDMENTS TO WEEKS 1–3 (consolidated)

Every one of these touches code another week depends on. Do them in the day they are listed, not opportunistically.

| # | Week | Amendment | Day |
|---|---|---|---|
| A1 | All | Renumber decision IDs to namespaced form (§0.1) | 22 |
| A2 | W2 | `extract_faces` computes pHash + dHash from the in-memory web derivative | 22 |
| A3 | W2 | `extract_faces` **retains and uses** 2d106 landmarks for quality scoring | 23 |
| A4 | W2 | Gallery index replaced: `(guest_id, status, cluster_rank, similarity DESC)` | 23 |
| A5 | W3 | ZIP `match_set_hash` must include the `best_only` flag | 23 |
| A6 | W2 | **Reference matrix cache moves from Redis to process memory** (W4.D12) | 24 |
| A7 | W3 | Selfie-search face matrix cache moves to process memory | 24 |
| A8 | W2 | `load_reference_matrix` decrypts; norm/finite assertions run post-decrypt | 24 |
| A9 | W2 | `scripts/verify_embeddings.py` updated for ciphertext | 24 |
| A10 | W1 | `Guests.consent_given_at` backfilled into `ConsentRecords`, column deprecated | 25 |
| A11 | W2/W3 | Media endpoints `302` to presigned URLs when `storage_tier='s3'` | 26 |
| A12 | W3 | ZIP builder uses multipart-to-object-storage; disk guard → quota guard | 26 |
| A13 | W2 | The "nothing outside `StorageBackend` touches `open()`" rule becomes an enforced lint test | 26 |
| A14 | All | Migrations run as a one-shot job, never on app startup | 27 |

---

# 10. NEW ENVIRONMENT VARIABLES

```text
# Dedup
DEDUP_ENABLED=true
DEDUP_PHASH_MAX=6
DEDUP_DHASH_MAX=12
DEDUP_TIME_WINDOW_S=30

# Quality
QUALITY_SCORING_ENABLED=true
SCORING_MODEL_VERSION=q1
QUALITY_W_SHARPNESS=0.30
QUALITY_W_EYE_OPEN=0.25
QUALITY_W_FRONTALITY=0.20
QUALITY_W_EXPOSURE=0.15
QUALITY_W_SMILE=0.10
SMILE_MODEL=geometric

# Crypto
ENCRYPT_REFERENCE_EMBEDDINGS=true
KMS_PROVIDER=local            # local | aws
MASTER_KEY=                   # local provider only, base64, 32 bytes
AWS_KMS_KEY_ID=
KEY_CACHE_TTL_S=600

# Privacy / retention
DEFAULT_RETENTION_DAYS=365
ERASURE_GRACE_DAYS=7
ERASURE_DELETES_PHOTOS=false
DATA_EXPORT_TTL_H=24
CONSENT_POLICY_VERSION=v1
SELFIE_LOG_RETENTION_DAYS=30

# Storage
STORAGE_BACKEND=s3            # local | s3
STORAGE_DELIVERY=presigned    # proxy | presigned
S3_ENDPOINT_URL=
S3_REGION=
S3_BUCKET=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_FORCE_PATH_STYLE=false
PRESIGN_TTL_S=300
ZIP_MULTIPART_THRESHOLD_MB=100
STORAGE_QUOTA_GB=200

# Deployment / observability
ENVIRONMENT=production
PUBLIC_BASE_URL=
SENTRY_DSN=
LOG_FORMAT=json
LOG_LEVEL=INFO
METRICS_ENABLED=true
BACKUP_BUCKET=
```

Every variable documented in the README with type, default, and blast radius if set wrong.

---

# 11. FILE STRUCTURE ADDITIONS

```text
backend/
├── api/endpoints/
│   ├── clusters.py
│   ├── quality.py
│   ├── privacy.py            # consent, export, erasure (organizer side)
│   └── public_privacy.py     # consent, export, erasure (guest side)
├── models/
│   ├── photo_cluster.py
│   ├── consent_record.py
│   ├── erasure_request.py
│   ├── data_export.py
│   └── audit_log.py
├── services/
│   ├── hashing.py
│   ├── dedup_service.py
│   ├── face_quality.py
│   ├── ranking_service.py
│   ├── crypto/
│   │   ├── key_provider.py
│   │   ├── envelope.py
│   │   └── embedding_crypto.py
│   ├── privacy/
│   │   ├── consent_service.py
│   │   ├── export_service.py
│   │   └── erasure_service.py
│   └── storage/
│       └── s3.py
├── workers/
│   ├── dedup.py
│   ├── quality.py
│   └── privacy.py
└── observability/
    ├── logging.py
    └── metrics.py

frontend/app/
├── events/[id]/clusters/
├── events/[id]/settings/retention/
├── admin/erasure-requests/
└── g/[access_code]/
    ├── my-data/
    └── delete/

scripts/
├── backfill_hashes.py
├── backfill_quality.py
├── backfill_encrypt_embeddings.py
├── verify_encryption.py
├── migrate_storage.py
├── calibrate_dedup.py
├── audit_privacy.py
└── dr_drill.py

deploy/
├── docker-compose.prod.yml
├── Caddyfile
├── backup.sh
└── restore.sh

docs/
├── dedup.md
├── quality.md
├── crypto.md
├── costs.md
├── deployment.md
├── perf-week4.md
└── policy/consent-v1.md
```

---

# 12. TESTING CHECKLIST (Day 28 gate)

**Dedup**
- [ ] Identical image resized 50% → clustered · JPEG q60 → clustered · ±10% brightness → clustered
- [ ] Same backdrop, 3 hours apart → **not** clustered (temporal guard)
- [ ] Two different dark low-detail photos → **not** clustered (dHash corroboration)
- [ ] Transitive burst A~B~C with A≁C → single cluster
- [ ] Re-run produces identical cluster IDs
- [ ] "Not duplicates" exclusion survives a re-run
- [ ] Deleting a photo in a cluster does not orphan or delete the cluster's other photos
- [ ] Dedup never changes any `Matches` row

**Quality & ranking**
- [ ] Blurred fixture scores low sharpness; closed-eye fixture scores low eye-openness; profile scores low frontality
- [ ] Two guests in one burst receive **different** `cluster_rank=1` photos
- [ ] Photo with no cluster gets `cluster_rank = 1`
- [ ] Reweighting + rescore changes ranks and bumps `scoring_model_version`; old rows still queryable
- [ ] Gallery default hides burst siblings; "show all" reveals them; ZIP default includes them
- [ ] `best_only` ZIP and full ZIP produce **different** cache entries

**Crypto**
- [ ] Round-trip encrypt/decrypt is bit-exact for all 1,000 reference embeddings
- [ ] Ciphertext swapped between two guests → decrypt fails (AAD)
- [ ] Nonce is unique across every row
- [ ] Deleting `wrapped_dek` makes recovery impossible, **including from a pre-shred backup restore**
- [ ] Deleting `wrapped_kek` shreds a whole event
- [ ] Full-event match ≤ 5 s and new-guest match ≤ 1 s **with** decryption
- [ ] Plaintext `FaceEmbeddings.embedding` column no longer exists
- [ ] Plaintext vectors are **not** present in Redis (scan every key)
- [ ] Restore without the master key → biometrics inert, app degrades loudly rather than silently mis-matching

**Privacy**
- [ ] Consent recorded with correct policy version at all three capture points
- [ ] `ConsentRecords` cannot be updated or deleted by the app role
- [ ] `AuditLog` cannot be updated or deleted by the app role
- [ ] Export contains no embeddings, phone leakage to third parties, storage keys, or similarity scores
- [ ] Erasure request revokes the magic link **immediately**, before the grace period
- [ ] Post-erasure: DB grep, object-storage listing, Redis scan, and log grep for the guest's identifiers all return zero
- [ ] Post-erasure: a full match re-run does not resurrect the guest anywhere
- [ ] Post-erasure: their `PhotoFaces` are redacted, `is_matchable=false`, crops gone, photos intact
- [ ] Other guests' matches to the same photos are unaffected
- [ ] Deletion certificate hash verifies against the audit record
- [ ] Retention dry-run output matches what the real purge destroys
- [ ] `SelfieSearchLogs` older than 30 days are gone

**Storage & delivery**
- [ ] Lint test: zero filesystem calls outside `services/storage/`
- [ ] Migration is resumable; interrupting and restarting is a no-op for done objects
- [ ] Every migrated object's checksum matches
- [ ] Dual-read serves `local` and `s3` tiered objects correctly in the same event
- [ ] Presigned URL expires exactly at TTL and then 403s
- [ ] Authorization is enforced **before** any URL is signed — Organizer A never receives a signed URL for Organizer B's object
- [ ] Every Week 3 negative-authorization test still passes against presigned delivery
- [ ] Bucket has no public-read ACL; public access block is on
- [ ] ZIP > 100 MB uses multipart and is byte-correct
- [ ] Storage quota exceeded → `503` with retry hint, no partial objects left behind

**Deployment**
- [ ] Fresh deploy from the runbook, zero undocumented steps
- [ ] Migrations run once, not once per replica
- [ ] Unhealthy backend removed from rotation by Caddy
- [ ] TLS valid; HTTP redirects; HSTS present; W3 security headers intact in prod
- [ ] Logs contain no token plaintext, phone numbers, storage keys, or vectors
- [ ] Sentry captures a deliberately raised error with the right release tag
- [ ] `/metrics` reports queue depth that visibly moves during a batch
- [ ] Flower is not reachable from the internet
- [ ] Nightly backup exists in the separate bucket, contains no master key
- [ ] DR drill completes; RTO and RPO recorded

---

# 13. FINAL ACCEPTANCE TEST

Week 4 is not complete until this runs end to end on the **deployed** environment:

```text
deploy from runbook
        ↓
one-shot migrations
        ↓
seed 500 guests + 5,000 photos
        ↓
ingest → faces → hashes → clusters → quality scores
        ↓
full-event match (encrypted references, in budget)
        ↓
per-guest cluster ranking
        ↓
500 magic links generated
        ↓
portal loads over HTTPS on a real phone, best-of-burst by default
        ↓
"show all N similar" expands correctly
        ↓
single download via presigned URL
        ↓
ZIP (best_only + full, distinct caches) built to object storage
        ↓
guest opens /my-data, exports JSON, requests erasure
        ↓
link dies immediately; grace period observed; purge executes
        ↓
crypto-shred verified against a pre-shred backup restore
        ↓
full match re-run: erased guest does not reappear; other guests unaffected
        ↓
storage migration verified; nothing served from local disk
        ↓
backup taken; host destroyed; restored from runbook; integrity verified
        ↓
every §5 number measured and written to docs/perf-week4.md
```

---

# 14. [FLAG — DO NOT GUESS] Open decisions needing a human call

**W4.F1 — Does erasure have to delete the photograph itself?** I have defaulted to *no* (`ERASURE_DELETES_PHOTOS=false`): the image is the photographer's work, other data subjects appear in it, and the biometric linkage is what gets destroyed. That is a defensible engineering position and it is genuinely not obviously the legally correct one under every regime. The config switch exists so the answer can change without a code change. **This one needs counsel, and it needs them before you run a real event, not after the first request arrives.** Related sub-question: if the answer is "delete it," what happens to the other three guests whose galleries contain that photo?

**W4.F2 — Master key custody.** AWS KMS (audit trail, rotation, HSM-backed, ~$1/month/key + per-call, ties you to AWS) versus an env-injected key managed by your secret store (free, portable, and entirely dependent on your operational discipline). I have built both behind `KeyProvider`. Pick one for production and write down who can access it and what happens if that person is unavailable — a crypto-shredding system with a lost master key is a data-loss event, and one with a carelessly-held master key is theatre.

**W4.F3 — Object storage provider, and this is a money decision.** ~100 GB egress per fully-delivered event. AWS S3 ≈ $9/event in egress alone before re-downloads; Cloudflare R2 ≈ $0 egress with S3-compatible API; Backblaze B2 ≈ $0 egress via the Bunny/Cloudflare alliance. Since `S3Storage` is endpoint-configurable this is a config choice, not a code choice, but it changes your unit economics by roughly an order of magnitude and it should be decided before Day 26 so the migration runs once. Verify current pricing directly — these numbers move.

**W4.F4 — Managed Postgres provider and pgvector.** RDS, Supabase, Neon, and DigitalOcean all support pgvector but differ on version, extension-creation privileges, and connection limits. Confirm the specific one before Day 27; discovering on deployment day that you cannot `CREATE EXTENSION` is a bad afternoon.

**W4.F5 — Can an organizer deny an erasure request?** I have specced *no* — the organizer can expedite but not veto, because the guest is the data subject. If your commercial reality requires an organizer hold (a contractual dispute, an ongoing legal matter), that needs an explicit state in `ErasureRequests` and a documented justification field, and it needs to be a deliberate product decision rather than an emergent one.

**W4.F6 — Retention default of 365 days.** Reasonable for a wedding photographer whose clients come back for anniversaries; possibly far too long for a corporate event. Confirm, and consider making it a required field at event creation rather than a silent default — a default retention period is a decision made by whoever wrote the config file, which should not be how it works.

**W4.F7 — Does dedup grouping apply to the organizer's grid by default, or only the guest gallery?** I have defaulted to guest-gallery-on, organizer-grid-toggle. Photographers sometimes very much want to see every frame; guests never do.

**W4.F8 — GPU for face extraction in production.** Off by default. Turning it on cuts extraction from ~30 min to ~6 min per event at meaningfully higher hourly cost. Whether that is worth it depends on how long after the last shutter click your clients expect their photos, which is a business answer.

---

# 15. WHAT THE AI AGENT MUST NOT DO

```text
Do NOT auto-delete any photo during dedup, under any threshold, ever
Do NOT pick one "best photo" per cluster globally and use it for all guests
Do NOT re-run face detection to obtain landmarks that detection already produced
Do NOT score blur on the 256px crop, or on the original, or on a mix
Do NOT encrypt PhotoFaces.embedding (it breaks the matching hot path and the pgvector fallback)
Do NOT cache decrypted biometric vectors in Redis
Do NOT drop the plaintext embedding column in the same migration that populates the encrypted one
Do NOT put the master key anywhere a database backup can reach
Do NOT let an erasure leave the guest's PhotoFaces embeddings matchable
Do NOT allow UPDATE or DELETE on AuditLog or ConsentRecords from the app role
Do NOT do a big-bang storage cutover with no per-object tier and no resumability
Do NOT sign a presigned URL before the ownership check passes
Do NOT run Alembic on application startup with multiple replicas
Do NOT expose Flower, /metrics, or Sentry debug endpoints publicly
Do NOT train a model
Do NOT introduce Kubernetes, a second database, or a dedicated vector database
Do NOT build multi-organizer, payments, kiosk mode, multilingual, or watermarking
```

---

# 16. STOP CONDITIONS

Stop and report before proceeding if:

1. Week 2's `extract_faces` discards 2d106 landmarks and cannot be changed without re-detecting.
2. `PhotoFaces.crop_key` objects do not exist for the seeded event (Day 23 review UI and Day 25 erasure both assume them).
3. Week 3's `Matches.status = pending_review` amendment was never applied — the guest gallery predicate is wrong and dedup/ranking will faithfully rank unreviewed guesses.
4. Reference embeddings are not uniformly L2-normalized (the Week 2 backfill did not actually run) — do not encrypt a mixed set.
5. Any code outside `services/storage/` touches the filesystem in a way that cannot be refactored in a day.
6. The chosen managed Postgres cannot create the `vector` extension.
7. The available object-storage budget cannot hold originals + derivatives + the ZIP cache for one event (~60 GB working set).
8. There is no legal sign-off available on W4.F1 and a real event is scheduled — encryption and export can ship, but do not ship an erasure button whose semantics nobody has approved.
9. Existing backups have never been restore-tested, in which case that is Day 27's first task, not Day 28's last.

Report as:

```text
BLOCKER
Current state:
Expected state:
Files affected:
Recommended fix:
Estimated cost to fix:
```

Then wait.

---

# 17. CORE PRINCIPLE

Weeks 1–3 built a system that works. Week 4 builds a system you can point at the internet, hand to a paying client, and defend in a conversation with their lawyer.

The engineering is mostly easy — a 64-bit hash, a weighted average, an AES-GCM wrapper, a boto3 client. What is hard is the **semantics**: what "duplicate" means when two guests disagree about which frame is best, what "delete my data" means when the data is a photograph someone else owns and four other people are also in, and what "encrypted" means when the decryption key is sitting in the same process that serves the internet.

Ranked by what will actually hurt you:

```text
1. An erasure that leaves biometric residue behind
2. A dedup that hides a guest's only good photo
3. A master key stored somewhere a backup can reach
4. A presigned URL signed before the authorization check
5. A storage migration that cannot be resumed
6. A best-photo picked globally instead of per guest
7. Consent recorded without the version of the text the guest actually saw
```

Get those seven right. Everything else in this document is implementation detail.