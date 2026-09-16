# ADR 0002: pgvector as Single Matching Path

## Status
Accepted

## Context
The system previously had two competing similarity paths: computing cosine similarity in-memory via numpy in `worker-io`, and `pgvector` in the database. Computing it in-memory duplicates logic, truth, and is inefficient.

## Decision
`pgvector` will be the single source of truth and execution for matching. We will store embeddings L2-normalised as `vector(512)`, use `vector_cosine_ops` with HNSW, and push compute to the database. The numpy path will be removed or explicitly labeled as a fallback.
