# Snaptracer

Snaptracer helps event organizers upload photos, match them to guests, and share private galleries.

## Repository map

| Path | Contents |
| --- | --- |
| `frontend/` | Next.js web app and guest gallery |
| `backend/` | FastAPI, database migrations, Celery workers, and tests |
| `ai-service/` | Face recognition service |
| `docker/` | Database and reverse proxy configuration |
| `scripts/` | Setup, seeding, and maintenance tools |
| `docs/` | Architecture, operations, API, and privacy documentation |

The root `docker-compose*.yml` files define the production, development, and test stacks. `Makefile` contains shortcuts for starting and testing them. Copy `.env.example` to a local `.env` and configure it before running a stack.

## Development

- `make dev` starts the development stack.
- `make test` runs the backend test suite with isolated test services.
- In `frontend/`, run `npm ci`, then `npm run dev` for the web app or `npm run tsc` for a type check.

See [operations](docs/OPERATIONS.md), [architecture](docs/ARCHITECTURE.md), and the [runbook](docs/runbook.md) for deployment and maintenance details.
