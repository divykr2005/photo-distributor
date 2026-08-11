# AI Event Photo Distribution

An AI-powered event photo platform: guests register with a face capture, photographers upload event photos, the system matches faces and delivers personalized galleries.

**Week 1 scope:** Registration + storage infrastructure (auth, events, guests, face embeddings).

---

## Folder Structure

```
photo_distr/
├── backend/          # FastAPI — auth, events, guests, face embeddings
│   ├── api/          # Route handlers (endpoints/)
│   ├── core/         # Config, security (JWT, bcrypt)
│   ├── database/     # SQLAlchemy session + Alembic migrations
│   ├── middleware/   # Rate limiting
│   ├── models/       # SQLAlchemy ORM models
│   ├── repositories/ # DB access layer
│   ├── schemas/      # Pydantic request/response models
│   ├── services/     # Business logic (auth)
│   ├── worker/       # Face processor (DeepFace/ArcFace) + task runner
│   └── uploads/      # Local file storage (dev only)
├── frontend/         # Next.js 14 + TypeScript + Tailwind
│   ├── app/          # App router pages
│   │   ├── (auth)/   # /login, /register
│   │   └── (dashboard)/ # /dashboard, /events, /guests
│   ├── components/   # Reusable UI + layout components
│   ├── contexts/     # AuthContext (JWT in memory)
│   ├── lib/          # Axios API client (auto token refresh)
│   └── types/        # TypeScript interfaces
├── ai-service/       # Standalone FastAPI face embedding microservice
├── docker/           # init.sql (enables pgvector)
├── docker-compose.yml
└── .env.example
```

---

## Tech Stack

| Layer      | Choice                                      |
|------------|---------------------------------------------|
| Frontend   | Next.js 14, TypeScript, Tailwind CSS        |
| Backend    | FastAPI, Python 3.11, SQLAlchemy, Alembic   |
| Database   | PostgreSQL + pgvector extension             |
| AI         | DeepFace (ArcFace model, 512-dim embedding) |
| Auth       | JWT access token + opaque refresh token     |
| Storage    | Local filesystem (`backend/uploads/`)       |
| Docker     | docker-compose (db, backend, ai, frontend)  |

---

## Quick Start (Docker)

```bash
# 1. Clone and configure
git clone <repo-url>
cd photo_distr
cp .env.example .env
# Edit .env — set a strong JWT_SECRET

# 2. One-command startup
docker-compose up --build

# Services:
#   Frontend  → http://localhost:3000
#   Backend   → http://localhost:8000
#   API docs  → http://localhost:8000/api/v1/openapi.json (Swagger UI at /docs)
#   AI svc    → http://localhost:8001
```

Migrations run automatically on backend startup (`alembic upgrade head`).

---

## Local Development (without Docker)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with [pgvector](https://github.com/pgvector/pgvector) installed

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# Configure (copy and edit)
cp ../.env.example ../.env

# Run migrations
alembic upgrade head

# Start server
uvicorn main:app --reload --port 8000
```

### AI Service

```bash
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
# Create frontend env
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
# → http://localhost:3000
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable               | Default              | Description                         |
|------------------------|----------------------|-------------------------------------|
| `POSTGRES_DB`          | `eventphotos`        | Database name                       |
| `POSTGRES_USER`        | `postgres`           | Database user                       |
| `POSTGRES_PASSWORD`    | `password`           | **Change in production**            |
| `POSTGRES_HOST`        | `localhost`          | `db` when using Docker              |
| `POSTGRES_PORT`        | `5432`               | PostgreSQL port                     |
| `JWT_SECRET`           | —                    | **Required — use a random 64-char string** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`        | Access token lifetime               |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | `7`         | Refresh token lifetime              |
| `FRONTEND_URL`         | `http://localhost:3000` | CORS allowed origin              |

Frontend only needs `NEXT_PUBLIC_API_URL` in `.env.local`.

---

## API Overview

All endpoints are under `/api/v1`. Interactive docs: `http://localhost:8000/docs`

| Method | Path                          | Description                   |
|--------|-------------------------------|-------------------------------|
| POST   | `/auth/register`              | Register organizer            |
| POST   | `/auth/login`                 | Login → access + refresh token |
| POST   | `/auth/refresh`               | Rotate refresh token          |
| POST   | `/auth/logout`                | Revoke refresh token          |
| GET    | `/auth/me`                    | Current user                  |
| GET    | `/dashboard/stats`            | Event + guest counts          |
| POST   | `/events`                     | Create event                  |
| GET    | `/events`                     | List events                   |
| GET/PUT/DELETE | `/events/{id}`        | Event CRUD                    |
| POST   | `/guests`                     | Register guest                |
| GET    | `/guests?page=&page_size=&search=&event_id=` | Paginated guest list |
| GET/PUT/DELETE | `/guests/{id}`        | Guest CRUD                    |
| POST   | `/guests/{id}/photo`          | Upload photo → run embedding  |

> **Security note:** The `embedding` vector is never returned in any API response.

---

## Data Model

```
Users → RefreshTokens
Users → Events → Guests → FaceEmbeddings (embedding vector(512))
Events → EventPhotos  (Week 2: matching pipeline)
```

---

## Testing

See [TESTING.md](TESTING.md) for the full checklist.

Quick smoke test after `docker-compose up`:

```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=test@example.com&password=password123'
```

---

## Roadmap

- **Week 2** — Bulk photo upload, pgvector similarity search (face matching)
- **Week 3** — Per-guest gallery, WhatsApp delivery
- **Week 4** — Cloud storage, duplicate removal, quality scoring
