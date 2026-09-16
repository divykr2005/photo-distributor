# Agent Instructions & Invariants

This file contains strict invariants and conventions that any agent working on this repository must follow.

## Invariants
- **NEVER edit `.env`**: Only ever edit `.env.example`. The `.env` file is local and agent-forbidden.
- **Alembic Revisions**: Every change to the database models must be accompanied by an Alembic migration revision.
- **Traefik Rules**: Never widen a Traefik router rule or expose unnecessary ports.

## Commands
Use the following `make` commands to interact with the repository:
- `make up`: Starts the local development environment.
- `make logs`: Tails the logs of the local environment.
- `make test`: Runs the test suite against the local isolated database.
- `make deploy`: Deploy targets.

## Repo Map
- `frontend/`: Next.js 14 web application.
- `backend/`: FastAPI REST API service and Celery tasks.
- `docker/`: Additional Docker configuration files.
- `docs/`: Architecture documentation and ADRs.
- `scripts/`: Utility scripts.
