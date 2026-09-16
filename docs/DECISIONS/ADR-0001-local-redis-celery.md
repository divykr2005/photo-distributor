# ADR 0001: Local Redis for Celery Broker

## Status
Accepted

## Context
Upstash Redis was originally considered for the Celery broker. However, Celery's default transport does blocking BRPOP long-polls and chatters significantly, which generates millions of commands on a serverless Redis. Upstash also aggressively closes idle connections.

## Decision
We will move the Celery broker to a local Redis container to avoid network overhead, excessive commands on a serverless provider, and idle connection closures. Upstash will only be considered if a cache that survives VM rebuilds is strictly necessary.
