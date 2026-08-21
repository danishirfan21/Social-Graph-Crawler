# V2 implementation plan

## Current flow

`POST /crawl/start` writes a `crawl_jobs` row and schedules FastAPI `BackgroundTasks`. The process-local task opens a new database session and runs a crawler. Discovery state is held in crawler memory. A process restart therefore loses queued/in-progress work; Redis is only used for readiness/cache connectivity.

## V2 flow

`POST /crawl/start` creates a PostgreSQL job and deduplicated frontier rows, then enqueues a small ARQ task containing only the job ID. Multiple ARQ worker processes claim frontier rows with PostgreSQL row locks, process one row at a time, persist graph results, and enqueue follow-up frontier work. PostgreSQL remains the source of truth; Redis is the durable broker and cross-worker throttle coordinator.

## Components introduced

| Component | Why it is necessary |
|---|---|
| ARQ + Redis | Async-native durable task delivery with independently restartable workers and retry scheduling. Celery is broader but adds a synchronous task model; Dramatiq is viable but ARQ better matches the existing async stack. |
| `crawl_frontier_items` | Durable discovery, unique per job/target, leases, attempts, error record, and observable progress. |
| PostgreSQL claim/lease | `FOR UPDATE SKIP LOCKED` gives workers safe competing claims. Expired leases are returned to queued state for at-least-once recovery. |
| Redis source throttle | A small atomic next-allowed-at key coordinates a source policy across workers. |
| Prometheus metrics | Lightweight counters/gauges/histograms exposed at `/metrics`; no Grafana container is needed. |
| Deterministic fixture scenarios | Make success, retry, permanent failure, duplicate discovery, and slow processing demonstrable without external credentials. |

## Explicitly out of scope

External crawler frontier expansion, robots.txt, proxies, sharding, user authentication, Kubernetes, Kafka, Grafana, browser scraping, and internet-scale benchmarking. Existing graph APIs remain intact.

## Migration strategy

1. Add frontier schema and queue dependencies.
2. Replace the FastAPI background-task runner with an ARQ enqueue.
3. Keep crawler classes for future external-source adapters, but route V2 fixture processing through frontier workers.
4. Make job completion derived from frontier terminal state.
5. Retain database uniqueness constraints so re-delivery/retry is idempotent.

## Guarantees and recovery

The implementation is at-least-once: a worker may die after persistence but before acknowledgement. Node/edge/frontier constraints and upsert-style processing make repeated execution safe. A processing row has a lease; a worker requeues expired leases before claiming further work. It does not claim exactly-once execution.
