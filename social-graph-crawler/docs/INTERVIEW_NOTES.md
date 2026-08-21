# Interview notes

## Why Redis and PostgreSQL?

Redis/ARQ is the task broker and cross-worker throttle coordinator. PostgreSQL is the durable source of truth for jobs, frontier state, leases, errors, and graph data. A queue alone is not a durable crawl history.

## Why not keep the frontier entirely in Redis?

Redis is excellent for fast task delivery, but the crawler needs queryable, transactional, persistent progress and uniqueness constraints. PostgreSQL provides those properties and makes the job state inspectable after workers restart.

## What happens if a worker crashes?

A processing item has a lease. When the lease expires it can be returned to queued state through recovery/resume. Work may run again, so persistence is designed to be idempotent. This is at-least-once, not exactly-once.

## Can work execute twice?

Yes. That is an expected distributed-systems tradeoff. The frontier has a `(crawl_job_id, target)` constraint and nodes/edges have database uniqueness constraints, so repeated delivery does not create duplicate graph records.

## Why not exactly-once?

Exactly-once across a broker, worker, and database is expensive and often misleading. Persisting state and making writes idempotent is a simpler, defensible approach.

## How are duplicates prevented?

The database rejects duplicate frontier targets within a job and duplicate node/edge identities. Application checks improve responses, but constraints are the final authority.

## Why ARQ?

It is a small Redis-backed queue that fits the repository’s async FastAPI/aiohttp code. Celery and Dramatiq were viable alternatives, but ARQ avoids introducing a separate synchronous task model here.

## How would this scale?

**Implemented now:** independently scalable workers, Redis task delivery, PostgreSQL leases and deduplication. **Future:** partition frontier tables, use domain-aware scheduling, expand worker fleets, add richer tracing, and introduce proxy infrastructure only if a real source requires it.

## What would change for a real crawler?

Add robots.txt policy handling, stronger automatic lease recovery, source-specific adapters, operational alerts, authentication, and load tests against realistic controlled targets. Those are not currently implemented.
