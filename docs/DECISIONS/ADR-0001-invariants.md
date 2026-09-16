# ADR-0001 – Repository Invariants

## Status
Accepted

## Context
The repository contains multiple services (FastAPI backend, Next.js frontend) and deployment scripts. To keep the project maintainable, secure, and reproducible, a set of immutable invariants is required.

## Decision
The following invariants must never be violated:

1. **Never edit `.env`** – the local environment file is for developer‑specific secrets only. Agents must edit `.env.example` instead and keep `.env` listed in `.gitignore`.
2. **Alembic Revisions** – any change to database models must be accompanied by an Alembic migration revision. CI will fail if a model change lacks a migration.
3. **Traefik Rules** – never widen a Traefik router rule or expose unnecessary ports. Only the defined routes in `docker/traefik.yml` may be used.

These invariants are documented here and will be enforced by code reviews and CI checks.
