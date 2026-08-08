# AI Event Photo Distribution Platform — Week 1 Build Prompt

## Role / Context (for whoever/whatever is building this)

You are building the foundation layer of a multi-week project. The end product is an AI-powered event photo platform: guests register with a face capture, photographers upload event photos, the system matches faces and delivers personalized galleries via WhatsApp/link. None of that matching/delivery pipeline exists yet. This week is strictly **registration + storage infrastructure** — the plumbing everything else will plug into later.

Build only what's listed under "Today's Task" for each day. Do not pull forward features from the Long-Run Scope section, even if it seems quick — half-built matching/notification code with no proper backing this week creates rework later.

---

## Tech Stack (locked for this project)

| Layer | Choice |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, React Hook Form, Axios |
| Backend | FastAPI, Python, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL + pgvector extension |
| AI | InsightFace, OpenCV |
| Auth | JWT (access + refresh token) |
| Storage (dev only) | Local filesystem |
| Containerization | Docker + docker-compose |

---

## Week 1 Definition of Done

- [ ] Organizer can register and log in (JWT + refresh token)
- [ ] Organizer can create/edit/delete events
- [ ] Organizer can register a guest against an event
- [ ] Guest face can be captured via webcam or uploaded manually
- [ ] A 512-dim face embedding is generated and quality-checked before being stored
- [ ] Guest list is searchable, filterable, paginated
- [ ] Dashboard shows live counts (events, guests, registered today)
- [ ] Full stack runs via `docker-compose up`
- [ ] API documented (FastAPI auto-docs is enough)
- [ ] README explains setup + folder structure

> [!IMPORTANT]
> **Explicitly out of scope this week:** face matching, photo upload/gallery, WhatsApp/SMS/notifications, background workers (Celery/Redis), analytics, ZIP download, dedup/blur/smile scoring, live matching, cloud deployment, payments, multi-organizer support.

---

## Day-by-Day Plan

### Day 1 — Project skeleton + Auth backend

**Today's task:**

- Scaffold `frontend/`, `backend/`, `ai-service/`, `docs/`, `docker/`
- Backend app structure: `api/`, `models/`, `schemas/`, `services/`, `repositories/`, `utils/`, `middleware/`, `core/`, `database/`
- Postgres running via Docker with `pgvector` extension enabled
- `Users` table + Alembic migration
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me` — password hashing, JWT issuance
- Rate limit on login endpoint

**Done when:** Can register an organizer and receive a valid JWT via curl/Postman.

---

### Day 2 — Auth frontend + Dashboard shell

**Today's task:**

- `/login`, `/register` pages with React Hook Form + validation
- JWT storage strategy (httpOnly cookie or memory + refresh flow) — no localStorage for tokens
- Protected route wrapper
- `/dashboard` shell: Navbar, Sidebar, empty stat cards (Total Events / Total Guests / Registered Today), navigation to Events/Guests/Settings

**Done when:** A registered organizer can log in and land on a dashboard shell with working nav.

---

### Day 3 — Event management (full stack)

**Today's task:**

- `Events` table + migration (title, description, location, date, status, created_by)
- `POST/GET/PUT/DELETE /events`, `GET /events/{id}`
- `/events`, `/events/new`, `/events/{id}` pages — create/edit/delete/list UI
- Wire dashboard's "Total Events" card to real data

**Done when:** Organizer can create, edit, delete, and view events end-to-end through the UI.

---

### Day 4 — Guest registration + Camera module

**Today's task:**

- `Guests` table + migration
- `POST/GET/PUT/DELETE /guests`, `GET /guests/{id}`
- Guest registration form (first/last name, phone, email, gender, notes, event select)
- Camera module: open camera, capture, retake, upload-from-device fallback, image preview
- Client-side validation (phone format, required fields, file size/type)

**Done when:** A guest record can be created with either a webcam capture or an uploaded image (embedding not generated yet).

---

### Day 5 — Face embedding service + quality gate

**Today's task:**

- `ai-service`: InsightFace pipeline — detect face → generate 512-dim embedding
- Quality checks before accepting: no face, multiple faces, blurry (Laplacian variance), too dark, face too small, face rotated too much
- Return specific, actionable error messages per rejection reason
- `FaceEmbeddings` table (guest_id, embedding vector(512), model, quality_score) + migration
- `POST /embedding` wired into guest registration flow

**Done when:** Registering a guest either succeeds with a stored, quality-passed embedding, or fails with a clear reason (not a generic error).

---

### Day 6 — Guest list + Profile page + Dashboard wiring

**Today's task:**

- `/guests` table view: name, phone, event, registration date — search, filter, pagination
- `/guests/{id}` profile page: guest info, reference photo, registration details, embedding status (generated/failed/pending)
- Wire remaining dashboard cards to real counts
- Toast notifications + loading spinners across forms

**Done when:** Full guest journey (list → profile) works with real data, no dead UI states.

---

### Day 7 — Hardening, Docker, docs, testing

**Today's task:**

- `docker-compose.yml` covering frontend, backend, ai-service, postgres — one-command startup
- Run through full testing checklist (below)
- Security pass: hashed passwords, protected routes, input validation everywhere, embeddings never returned in API responses
- Finalize API docs, write README (setup steps, folder structure, env vars)
- Dark-mode-ready, responsive check on all pages

**Done when:** Fresh clone + `docker-compose up` + README instructions = working app, no manual fixes needed.

---

## Data Model (Week 1)

> [!NOTE]
> **[FIX] New vs v1:** added `RefreshTokens` table; `Events.status` is an enum;
> `Guests` gains `consent_given_at`, `embedding_status`, `updated_at`;
> `FaceEmbeddings` gains `model_version`, `embedding_dim`, `updated_at`;
> `guest_id` is one-to-many (no UNIQUE); `image_path` is a storage key.

```
Users              RefreshTokens       Events              Guests                FaceEmbeddings
-----              -------------       ------              ------                --------------
id                 id                  id                  id                    id
name               user_id (FK)        title               event_id (FK)         guest_id (FK)  ← no UNIQUE
email              token               description         first_name            embedding vector(512)
password_hash      expires_at          location            last_name             model_version
created_at         revoked             date                phone                 embedding_dim
updated_at         created_at          status (enum)       email                 quality_score
                                       created_by (FK)     gender                created_at
                                       created_at          notes                 updated_at
                                       updated_at          image_path (storage key)
                                                           consent_given_at
                                                           embedding_status
                                                           created_at
                                                           updated_at
```

---

## Testing Checklist (Day 7 gate)

### Happy path

- [ ] Auth (register + login + JWT)
- [ ] Create Event
- [ ] Edit Event
- [ ] Delete Event
- [ ] Register Guest
- [ ] Capture Face
- [ ] Upload Image
- [ ] Generate Embedding
- [ ] Store Embedding
- [ ] View Guest
- [ ] Search Guest
- [ ] Filter Guest
- [ ] Pagination
- [ ] Docker cold-start (from seed script)

### [FIX] Negative / edge cases (were missing in v1)

- [ ] Access a protected route with **no token** → 401
- [ ] Access with an **expired access token**, confirm silent refresh recovers
- [ ] **Refresh with a revoked/rotated token** → 401
- [ ] **Duplicate email registration** → clear 409/validation error
- [ ] **Invalid login** (wrong password) → generic 401, rate limit trips after N tries
- [ ] Guest image with **no face / multiple faces / blurry / too dark** → specific error
- [ ] **Oversized / wrong-type file** upload → rejected client- and server-side
- [ ] Delete a guest → confirm **FaceEmbeddings row cascades**
- [ ] Confirm **embedding vector never appears** in any API response

---

## Long-Run Scope (context only — DO NOT build yet)

> [!CAUTION]
> Kept so this week's schema/format/boundary decisions don't box out future phases. **Do NOT implement any of this during Week 1.**

**Week 2 — Matching pipeline:** photographer bulk photo upload · background
workers (Celery/RQ + Redis) · pgvector similarity search (add IVFFlat/HNSW index
here) · match confidence threshold tuning.

**Week 3 — Delivery + Admin:** per-guest gallery + ZIP download · WhatsApp (Twilio)
notification with a link (not raw images) · admin dashboard (registered, uploaded,
matched, pending, messages sent, accuracy).

**Week 4 — Quality & Scale:** duplicate removal (perceptual hashing) · photo blur +
smile/quality scoring to pick best photo · multi-face detection per photo · cloud
deployment + S3-equivalent storage (swap [DECISION D3] backend) · consent +
data-deletion workflow/UI · encrypted/hashed embeddings.

**Beyond MVP:** multi-organizer support · payments/billing · offline/kiosk capture ·
SMS fallback + multilingual UI · search-by-selfie (no prior registration).

> [!WARNING]
> Reminder: if you hit a Week 1 decision this doc has NOT already locked
> (D1–D6), flag it — do not guess.
