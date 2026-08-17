[13/08, 09:40] Here's Week 3, written to the same contract as your Week 1 / Week 2 docs — locked decisions, hard numbers, day-by-day, and an explicit "flag, don't guess" list. I've kept your Day 15–21 spine and added the pieces that were missing (public media serving, visibility predicate, token hashing, ZIP economics, notification idempotency, EXIF stripping, abuse defense).

---

# Week 3 Build Prompt — Delivery Layer (Magic Links → Public Portal → Selfie Search → Downloads → Notifications)

**Scale target locked, unchanged from Week 2: 1 event = 500 guests, 5,000 photos, ~25,000 photo-faces.** Derived Week 3 numbers: ~50 matched photos per guest average, ~200 MB of originals per guest ZIP, up to 500 concurrent-ish guests hitting the portal in the hours after an event (realistically 60–100 in the first hour). Build for that. Not for 50,000 guests.

---

## Role / Context

Weeks 1–2 delivered auth, events, guests, quality-gated reference embeddings, bulk photo ingest, Celery/Redis workers, `PhotoFaces`, and an organizer-facing match review queue. Everything so far lives **behind organizer login**.

This week you open a **second, unauthenticated surface** to the internet: the guest portal. That is a materially different security posture than anything built so far. Every endpoint added this week is reachable by anyone with a URL, so every endpoint added this week is rate-limited, enumeration-resistant, and returns a whitelisted field set. Treat `/api/v1/public/*` as hostile territory.

Week 4 (dedup, blur/smile ranking, S3, encrypted embeddings, data-deletion UI) is **not** built here.

---

## Week 3 Definition of Done

- [ ] Every registered guest has a revocable, expiring, hashed-at-rest access token; organizer can generate, rotate, and revoke it from the dashboard
- [ ] `/g/{access_code}` renders a mobile-first gallery of that guest's confirmed photos with no login, in ≤ 2.0 s p95 on 4G
- [ ] All public image bytes are served through a token-verified media endpoint — no direct storage paths, no guessable static URLs
- [ ] Walk-in attendee can upload a selfie at `/events/{id}/find` and see their photos in ≤ 3 s p95, with the selfie never persisted
- [ ] Single-photo high-res download works and **provably refuses** photos the token doesn't own
- [ ] Guest can request a ZIP; it is built by a worker, cached, TTL-expired, and streamed on completion — never built in the request thread
- [ ] Notification dispatch engine sends a link (never media) over a pluggable channel, is idempotent, retries with backoff, and honours opt-out
- [ ] Redis rate limiting live on every public route, with `429 + Retry-After`
- [ ] Seed script → 500 guests → 500 magic links → 50 portal loads → 20 ZIPs, all inside the perf budget
- [ ] `docs/public-api.md`, `docs/privacy.md`, `docs/notifications.md` written; `docker-compose up` still one command

> [!IMPORTANT]
> **Out of scope this week:** perceptual dedup, blur/smile best-photo ranking, analytics dashboard, S3/cloud deploy, payments, multi-organizer, encrypted embeddings, guest self-service data-deletion UI (Week 4), watermarking, print/e-commerce, face-based "unregister me" flows.

---

## Performance & Capacity Budget (this is the spec)

| Stage | Volume | Target | Notes |
|---|---|---|---|
| Token validation | 1 lookup | ≤ 30 ms p95 | indexed lookup on `token_hash`, no table scan |
| Portal first paint | 50 thumbs @ 400px (~40 KB) | ≤ 2.0 s p95 on 4G | lazy-load below fold, 24 thumbs above |
| Public media serve (thumb) | — | ≤ 120 ms p95 | `Cache-Control: private, max-age=3600`, ETag, 304 on revisit |
| Selfie embed | 1 image, CPU | ≤ 800 ms p95 | resize to 640px long edge before detect |
| Selfie match | 1 × 25k vectors | ≤ 50 ms | single NumPy matmul, cached matrix (see W3.D6) |
| Selfie end-to-end | — | ≤ 3.0 s p95 | including upload on 4G |
| Single photo download | ~4 MB original | starts streaming ≤ 300 ms | zero full-file buffering |
| ZIP build | ~50 photos / ~200 MB | ≤ 60 s p95 | `ZIP_STORED`, disk-bound |
| ZIP disk ceiling | — | 40 GB, TTL 48 h | ~200 concurrent cached ZIPs; beat sweeps hourly |
| Notification dispatch | 500 guests | ≤ 10 min | rate-limited per provider, not a thundering herd |

**Do the arithmetic before you write code:** JPEGs are already entropy-coded. `ZIP_DEFLATED` on 200 MB of JPEG buys you ~2% size and costs ~40 s of CPU per guest. `ZIP_STORED` is the correct choice and it is not close. Similarly, 500 guests × 200 MB = 100 GB if you cache every ZIP forever — you cannot, hence the TTL and ceiling.

---

## [DECISION] New locks for Week 3 (W3.D1–W3.D14)

Locked. Implement exactly this. Anything outside this list → flag it.

**W3.D1 — Token format.** `secrets.token_urlsafe(16)` → 22 chars, 128 bits of entropy. *(This overrides the draft's "16-character token" — 16 chars of base62 is ~95 bits and, more importantly, an unhashed guessable-length token in a URL that gets forwarded around WhatsApp groups deserves the full 128.)* URL shape: `/g/{access_code}`.

**W3.D2 — Tokens are hashed at rest.** Store `sha256(token)` in `token_hash` (UNIQUE, indexed). The plaintext is returned exactly once, at generation time, and never again — regeneration issues a new token. A database dump must not be a master key to every guest's photos. Comparison via indexed hash lookup, then `secrets.compare_digest` on the re-derived hash.

**W3.D3 — Token lifecycle.** Default `expires_at = event.date + 90 days`, per-event overridable. Fields: `revoked_at`, `last_accessed_at`, `access_count`. Rotation revokes the old token. Response codes: invalid/revoked → `404` with a generic body; expired → `410` with a "link expired, contact your organizer" body. Never leak whether a token *ever* existed.

**W3.D4 — Visibility predicate is defined once, in one place.** A single SQL/ORM helper `visible_matches(guest_id)` used by portal, download, ZIP, and counts alike:

```sql
WHERE m.guest_id = :guest_id
  AND m.status IN ('active', 'manually_added')
```

> [!NOTE]
> **[FIX] to Week 2:** this only works if review-band matches are *not* `active` on insert. Add `pending_review` to `Matches.status` and make `decision='review'` rows insert as `status='pending_review'`; organizer confirmation flips them to `'active'`. Ship this as a Week 2 data-model amendment migration on Day 15 before anything else. Without it, the portal leaks unreviewed guesses to guests — the single worst failure mode in this product.

**W3.D5 — Public media serving.** All guest-facing image bytes go through `GET /api/v1/public/media/{photo_id}/{variant}?token=...`, `variant ∈ {thumb, web, original}`. Every request re-checks the visibility predicate. No storage keys, filesystem paths, or `/static/` mounts exposed publicly. `original` is only reachable via the download route (W3.D8). Document `X-Accel-Redirect` / `X-Sendfile` as the production offload path in `docs/scaling.md`, but ship the Python streaming version this week.

**W3.D6 — Selfie search is ephemeral and never enrolls.** The uploaded selfie is processed in memory, embedded, matched, and discarded — no `image_path`, no `Guests` row, no `FaceEmbeddings` row. Persist only a `SelfieSearchLogs` row (IP hash, event, result count, latency, timestamp) for abuse forensics. The event's face matrix is cached in the worker/API process (`{event_id: (ids, np.ndarray)}`, invalidated on new-photo ingest, TTL 10 min) so the 51 MB load isn't paid per request.

**W3.D7 — Selfie search uses a stricter threshold than organizer matching.** `selfie_auto_confirm = auto_confirm + 0.03` (default 0.45), margin rule from D12 still applies, and results are capped at the top 200 photos. Rationale: an organizer-side false positive costs a click in the review queue; a selfie-search false positive hands a stranger someone else's photos. Asymmetric cost → asymmetric threshold. Record the value used in `SelfieSearchLogs`.

**W3.D8 — Selfie results are authorized by a short-lived session token, not by photo ID.** On a successful search, mint `search_session_id` (Redis, TTL 15 min) holding the exact set of matched `photo_id`s. Downloads from a selfie search require that session token and are checked against that stored set. Never trust a `photo_id` the client hands back.

**W3.D9 — ZIP jobs are cached, capped, and swept.** `generate_guest_zip` is idempotent on `(guest_id, match_set_hash)` where `match_set_hash = sha256(sorted(photo_ids))`; if a completed, unexpired archive with that hash exists, return it instantly. `ZIP_STORED`. Hard caps: 1,000 photos and 8 GB per archive, one in-flight job per guest. TTL 48 h, Celery beat sweep hourly, plus a disk-watermark guard that refuses new jobs above 80% and returns `503` with a retry hint.

**W3.D10 — Notifications send links, never media.** One `Notifier` protocol with adapters: `console` (dev default), `smtp`, `webhook`, `twilio_whatsapp`, `twilio_sms`. Channel selection is env/config-driven per event. WhatsApp sits behind a feature flag and is **not** on the Day 21 critical path (see the flagged item on template approval below).

**W3.D11 — Notification idempotency.** `UNIQUE (guest_id, channel, notification_type, dedupe_key)` on `NotificationLogs`, where `dedupe_key` defaults to the guest's current `token_hash` prefix + match-count bucket. Statuses: `queued | sending | sent | delivered | failed | skipped_opt_out | skipped_duplicate`. Retries: max 5, exponential backoff `60s × 2^n` with jitter, only on transient/5xx/429 provider errors — never on hard rejects (invalid number, unsubscribed).

**W3.D12 — Opt-out and quiet hours are honoured at dispatch time, not at queue time.** `Guests.notify_opt_out_at` (nullable). Quiet hours 21:00–08:00 in the event's local timezone → task re-scheduled with an ETA, not dropped. Every message carries an opt-out instruction.

**W3.D13 — Rate limits (Redis sliding window, keyed by IP and by token).**

| Route | Limit |
|---|---|
| `POST /public/events/{id}/search-selfie` | 5 / min / IP · 30 / hour / IP · 60 / min / event |
| `GET /public/guest/{code}` | 60 / min / IP · 600 / hour / IP |
| `GET /public/media/*` | 300 / min / token |
| `GET /public/photos/{id}/download` | 120 / min / token |
| `POST /public/guest/{code}/zip` | 3 / hour / token |

All return `429` with `Retry-After`. Limits live in config, not scattered decorators.

**W3.D14 — Public responses use a dedicated serializer.** A `PublicGuestSchema` that whitelists: first name, event title/date, photo count, photo IDs + variant URLs. Never: embeddings, phone, email, notes, other guests, internal IDs of matches, similarity scores, storage keys. Add a test that asserts the string `"embedding"` and the guest's phone number appear in **zero** public responses.

---

## Data Model (Week 3 additions)

```
GuestAccessTokens       NotificationLogs        ZipArchives             SelfieSearchLogs
-----------------       ----------------        -----------             ----------------
id                      id                      id                      id
guest_id (FK cascade)   guest_id (FK cascade)   guest_id (FK cascade)   event_id (FK cascade)
event_id (FK denorm)    event_id (FK denorm)    event_id (FK denorm)    ip_hash
token_hash (UNIQUE)     channel (enum)          match_set_hash          user_agent_hash
token_prefix            notification_type       photo_count             faces_detected
expires_at              dedupe_key              total_bytes             threshold_used
revoked_at              status (enum)           storage_key             results_count
last_accessed_at        provider                status (enum)           top_similarity
access_count            provider_message_id     error                   session_id
created_by (FK)         error                   expires_at              latency_ms
created_at              attempts                started_at              rejected_reason
updated_at              next_retry_at           finished_at             created_at
                        sent_at                 downloaded_count
                        delivered_at            created_at
                        created_at
                        updated_at
```

**Amendments to existing tables.** `Guests`: `notify_opt_out_at`, `last_notified_at`. `Matches.status`: add `pending_review` (W3.D4). `Events`: `portal_enabled`, `portal_expires_at`, `selfie_search_enabled`, `timezone`, `selfie_threshold` (nullable override).

**Indexes.** `UNIQUE (token_hash)`; `INDEX (guest_id, revoked_at)` on GuestAccessTokens. `UNIQUE (guest_id, channel, notification_type, dedupe_key)`; `INDEX (status, next_retry_at)` on NotificationLogs. `INDEX (guest_id, status, expires_at)` on ZipArchives. `INDEX (event_id, created_at)` and `INDEX (ip_hash, created_at)` on SelfieSearchLogs.

**Retention.** `SelfieSearchLogs` purged at 30 days by the same beat job that sweeps ZIPs. Write that in `docs/privacy.md`.

---

## Day-by-Day Plan

### Day 15 — Token system + Week 2 amendment + public API scaffold

**Today's task**

- Migration: `Matches.status` gains `pending_review`; backfill existing `decision='review'` rows from `active` → `pending_review`. **Do this first and verify counts before/after.**
- Migration: `GuestAccessTokens` + `Events`/`Guests` amendments.
- `POST /events/{event_id}/guests/{guest_id}/magic-link` — generate/rotate; returns plaintext once.
- `POST /events/{event_id}/magic-links/bulk` — generate for all guests missing a live token (you will need this for 500 guests; doing it one at a time from the UI is not a plan).
- `DELETE .../magic-link` — revoke.
- `GET /api/v1/public/guest/{access_code}` — validate, return `PublicGuestSchema` + counts.
- Public router with its own middleware stack: no JWT, rate limiter, strict CORS, security headers, request logging with token hash (never plaintext) — plumbing only, real limits Day 21.
- `visible_matches()` helper, used by the count endpoint. One implementation, imported everywhere.

**Done when:** curl with a valid code returns guest metadata and a correct photo count; expired → 410; revoked → 404; and no plaintext token appears in any log line.

---

### Day 16 — Public portal UI + media serving

**Today's task**

- `GET /api/v1/public/media/{photo_id}/{variant}?token=` with visibility re-check, ETag/304, `Cache-Control: private, max-age=3600`.
- **Strip EXIF (GPS especially) from `web` and `thumb` derivatives.** If Week 2 didn't, add it now and write a one-off re-derive task — publishing a guest's home coordinates because the photographer's camera had GPS on is a real incident, not a hypothetical.
- `GET /api/v1/public/guest/{access_code}/photos` — keyset pagination, 24/page, `?cursor=`.
- Route `/g/[access_code]`: mobile-first grid, responsive columns, skeleton loaders, lazy images, full-screen lightbox with swipe + keyboard nav, per-photo metadata (taken-at, filename), header with event title/date and photo count.
- States that must exist and look intentional: loading, empty ("no photos matched yet — check back after the photographer uploads"), expired link, invalid link, network error.
- No app shell, no navbar, no dashboard chrome, no login prompt anywhere on this page.

**Done when:** the link opens on a phone, scrolls smoothly through 50+ photos, and a second load is mostly 304s.

---

### Day 17 — Selfie search

**Today's task**

- Event face-matrix cache (W3.D6) with invalidation hook on photo-ingest completion.
- `POST /api/v1/public/events/{event_id}/search-selfie` — multipart, ≤ 10 MB, JPEG/PNG/HEIC, streamed, in-memory only.
- Reuse Week 1's quality gate verbatim for the selfie: no face / multiple faces / blurry / too dark / too small / too rotated → specific actionable message ("we found two faces — please upload a photo of just yourself").
- Match: top-1 with margin (D12), threshold W3.D7, cap 200, sorted by similarity desc; return photo IDs + thumb/web URLs bound to a fresh `search_session_id`.
- `/events/[eventId]/find` page: event branding, consent checkbox with clear biometric-use copy (see flagged item), camera capture + upload fallback (reuse the Week 1 camera module), live preview, per-reason error rendering, result grid reusing the Day 16 gallery components, "no matches" empty state with a retry hint.
- Honour `Events.selfie_search_enabled`; disabled → 404 the page.

**Done when:** a walk-in flow works on a phone in under 3 s, and a selfie of someone not in the event returns a clean zero-result state rather than three wrong faces.

---

### Day 18 — Downloads + access verification

**Today's task**

- `GET /api/v1/public/photos/{photo_id}/download?token={access_code}` — verifies via `visible_matches()`, streams the **original** in 1 MB chunks, `Content-Disposition: attachment; filename="{event-slug}-{photo-id}.jpg"` with a sanitized filename, correct `Content-Length` and `Content-Type`, `Accept-Ranges: bytes` and range support so mobile resume works.
- Same route accepts `?session={search_session_id}` for selfie-search users, validated against the Redis set (W3.D8).
- Increment a per-photo download counter (cheap `UPDATE`, or Redis counter flushed by beat — your call, document it).
- Portal UI: download button per photo, in the lightbox, plus a "download all" button that is wired to Day 20's endpoint and disabled with a tooltip until then.
- **Negative tests are the deliverable here, not the happy path:** photo from another event, photo matched to a different guest, photo whose match was `rejected_by_organizer`, photo in `pending_review`, expired token, revoked token, expired search session — all `403`/`404`, all covered by an automated test.

**Done when:** the authorization test suite is green and you cannot download a photo you don't appear in, including by ID-guessing.

---

### Day 19 — Notification dispatch engine

**Today's task**

- `NotificationLogs` migration + `Notifier` protocol + adapters: `console`, `smtp`, `webhook`, `twilio_sms`, `twilio_whatsapp` (flag-gated).
- Celery task `dispatch_guest_notification(guest_id, channel, notification_type)` — idempotency check, opt-out check, quiet-hours ETA reschedule, provider call, log transition, retry policy per W3.D11.
- Batch task `dispatch_event_notifications(event_id, channel)` — chunked, provider-rate-limited (default 10 msg/s, config), skips guests with zero visible photos, skips already-sent.
- Templates: email (HTML + text) and message body — event name, photo count, magic link, opt-out line. No images attached, no photos inline.
- Organizer UI: "Notify guests" on the event page → channel picker, dry-run preview showing recipient count and one rendered message, confirm dialog, then a live send-status table (queued / sent / failed / skipped) polling every 2 s.
- `POST /events/{id}/notifications/test` — send one to the organizer's own address/number before blasting 500 people.

**Done when:** a dry run reports accurate counts, a real console-adapter run writes 500 correct log rows, and re-running it sends zero duplicates.

---

### Day 20 — ZIP worker

**Today's task**

- `ZipArchives` migration; `POST /api/v1/public/guest/{token}/zip` → returns existing archive or enqueues; `GET /api/v1/public/guest/{token}/zip/{job_id}` → status polling (2 s, same convention as Week 2's D16).
- `generate_guest_zip(guest_id)`: resolve `visible_matches()` → `match_set_hash` → cache hit check → stream photos into a temp file with `zipfile.ZipFile(..., ZIP_STORED)` → atomic rename → set `expires_at = now + 48h` → update row. Update `photo_count`/`total_bytes` progressively so the UI can show real progress.
- Caps and guards per W3.D9, including the disk watermark.
- `GET /api/v1/public/guest/{token}/zip/{job_id}/download` — streamed, range-capable, sanitized filename.
- Beat task `sweep_expired_zips` hourly; also purges `SelfieSearchLogs` older than 30 days.
- Portal UI: "Download all (N photos, ~X MB)" → progress bar → download button, with a "this may take a minute" message and a resumable poll that survives a page refresh (store `job_id` in `sessionStorage`).

**Done when:** two rapid requests produce one job, a third after completion returns the cached archive instantly, and the sweep actually reclaims disk.

---

### Day 21 — Hardening, abuse defense, tests, docs

**Today's task**

- Redis sliding-window limiter applied per W3.D13; verify with a loop script that the 6th selfie in a minute gets `429 + Retry-After`.
- Enumeration pass: constant-time comparisons, uniform error bodies, uniform response timing on invalid vs valid tokens (add a small fixed delay on the failure path if timing differs measurably), no guest names in error text.
- Security headers on public routes: `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, restrictive CSP, `X-Frame-Options: DENY`, and `<meta name="robots" content="noindex,nofollow">` plus `robots.txt` disallow on `/g/*` and `/events/*/find` — magic links must not end up in a search index.
- Integration test suite: full guest journey (link → view → download → ZIP), full walk-in journey (selfie → results → download), plus every negative case in the checklist below.
- Load check: 50 concurrent portal loads + 10 concurrent selfie searches against the seeded event; record p95s in `docs/perf-week3.md` and compare against the budget table.
- Seed script extension: 500 guests → bulk magic links → simulated portal traffic → 20 ZIPs.
- `docs/public-api.md` (every public route, limits, error codes), `docs/privacy.md` (what's stored, what's ephemeral, retention windows, opt-out), `docs/notifications.md` (provider setup, template text, sandbox instructions), `docs/runbook.md` (revoke a leaked link, re-notify, clear stuck ZIPs, disk full).
- Dark-mode + responsive check on the two new public pages; they're the pages non-technical people will actually see.

**Done when:** fresh clone → `docker-compose up` → seed → a magic link opens on a real phone on the office wifi, downloads a photo, and gets its ZIP.

---

## Testing Checklist (Day 21 gate)

**Happy path:** generate link · bulk-generate 500 links · open portal · paginate past 24 · lightbox · single download · ZIP request → poll → download · selfie search hit · selfie download via session · notification dry run · notification real send · rotate token → new link works.

**Negative / security (this is the real gate):**

- [ ] No token / malformed token / random 22-char string → `404`, uniform body, uniform timing
- [ ] Expired token → `410`; revoked token → `404`; rotated-old token → `404`
- [ ] Download a photo matched to a **different guest** → `403`
- [ ] Download a photo in `pending_review` or `rejected_by_organizer` → `403`
- [ ] Media endpoint with a valid token but another event's `photo_id` → `403`
- [ ] Selfie search: no face / multiple faces / blurry / dark → specific messages, not generic 500
- [ ] Selfie search returns zero for a stranger's face (test with a held-out identity)
- [ ] Selfie download with a **stale/expired session** → `403`; with a `photo_id` not in the session set → `403`
- [ ] Rate limits trip at the documented thresholds on all five public routes, with `Retry-After`
- [ ] Oversized (> 10 MB) and wrong-type selfie upload rejected client- and server-side
- [ ] Two simultaneous ZIP requests → one job; cached ZIP returns without rebuild; expired ZIP rebuilds
- [ ] Disk above watermark → `503` with retry hint, no partial archives left behind
- [ ] Duplicate notification dispatch → `skipped_duplicate`, provider not called
- [ ] Opted-out guest → `skipped_opt_out`; quiet-hours send → rescheduled, not dropped
- [ ] Provider 429/5xx → retried with backoff; hard reject → not retried
- [ ] Delete a guest → tokens, notification logs, ZIP rows cascade; cached ZIP file is swept
- [ ] `"embedding"`, phone, email, storage keys, similarity scores appear in **zero** public responses
- [ ] EXIF GPS absent from every `web`/`thumb` derivative served publicly
- [ ] `/g/*` returns `noindex`; `robots.txt` disallows it

---

## [FLAG — do not guess] Open decisions needing your call

1. **WhatsApp provider and ownership.** Twilio vs Meta Cloud API direct, and who owns the WABA + sender number. **This has a lead time and belongs on Day 15, not Day 19:** the first outbound message to a guest is always outside the 24-hour customer-service window, so it must be a pre-approved template. Approval is usually minutes but can stretch to days if the template gets flagged, and the phone number/business verification step is slower than that. Submit the template text on Day 15 and build Day 19 against the `console` adapter regardless. (Provider policies change frequently — verify current template rules with Twilio/Meta docs before submitting.)
2. **Biometric consent for walk-in selfie search.** Processing a stranger's face for identification carries explicit-consent obligations under several regimes (India's DPDP Act, GDPR Art. 9, Illinois BIPA). I've specced a consent checkbox and non-persistence, which is the right default, but the exact copy and whether you need a linked privacy notice is a call for you or your counsel. I'm not a lawyer and this isn't legal advice — worth 20 minutes with someone who is before this goes live at a real event.
3. **Do selfie-search users get originals, or web-size only?** I've defaulted to same-as-registered-guests (originals). Restricting walk-ins to 1600px is a defensible anti-harvesting measure if you'd prefer it.
4. **Token-in-URL vs OTP gate.** A magic link forwarded into a family WhatsApp group is shared with everyone in it. Acceptable for a wedding, possibly not for a corporate event. Optional phone-OTP-on-first-open is a half-day; say the word and I'll slot it into Day 15.
5. **ZIP disk budget.** I've locked 40 GB / 48 h against your dev box. Confirm the actual available disk before Day 20.
6. **Portal branding.** Organizer logo/colours on `/g/*` — nice-to-have, currently unspecified, and it's the page clients judge you on. Include this week or defer to Week 4?

---

One structural note on your draft: it had Day 19 (notifications) sending the links and Day 21 (rate limiting) hardening the endpoints those links point to — meaning for two days there's a live, unthrottled public surface with 500 real links pointing at it. I've kept the day order because the dependency chain is right, but the `console` adapter is the default through Day 20 for exactly this reason. Don't send real messages to real guests until Day 21 is green.