# ADR 0003: Separate Celery Beat Container

## Status
Accepted

## Context
Celery Beat was co-located with a worker. If the worker ever scales up (`replicas: >1`), multiple schedulers would be created, causing periodic tasks to fire multiple times.

## Decision
Split Celery Beat into its own single-replica container to guarantee singleton scheduling and avoid duplicated maintenance tasks.
