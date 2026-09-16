# CLAUDE.md

## Repository Invariants

- **Never edit `.env`** – the local environment file is forbidden for agents. Edit only `.env.example` and keep `.env` in `.gitignore`.
- **Alembic Revisions** – any change to database models must be accompanied by an Alembic migration revision.
- **Traefik Rules** – never widen a Traefik router rule or expose unnecessary ports.

## Development Commands (Makefile)

```bash
# Spin up all services in the background
make up

# Follow logs from all containers
make logs

# Run the test suite (Docker‑Compose test environment)
make test

# Deploy the application (placeholder – configure your target)
make deploy
```
