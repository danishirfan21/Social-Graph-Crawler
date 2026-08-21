# V2 architecture plan

V2 should begin only after the local baseline continues to pass in Docker with PostgreSQL and Redis. Its goal is durable crawling, not an unnecessarily complex graph platform.

| Component | Problem solved / why here | Alternatives | When | Expected failure modes |
|---|---|---|---|---|
| Dedicated workers + queue | API background tasks disappear on restart and compete with requests. Use a Redis-backed worker queue with explicit job messages. | Celery, Dramatiq, ARQ. ARQ is a good initial fit for the async FastAPI code; Celery is appropriate if ecosystem breadth outweighs async simplicity. | Next | Redis outage, poison messages, duplicate delivery. |
| Retry and dead-letter queue | Separate transient HTTP failures from exhausted/invalid work. Keep error history for operator inspection. | Database-only retry table. | Next | Retry storms and infinite poison-message loops; cap attempts and use jitter. |
| Crawl frontier and URL canonicalization | Prevent duplicate crawling and make traversal resumable across workers. Normalize scheme, host, fragments, redirects, and source-specific identifiers before enqueue. | Per-job in-memory sets (current approach). | Next | Canonicalization bugs can collapse distinct resources or miss duplicates. |
| Per-domain throttling + robots.txt | Respect upstream policies across all workers rather than per process. Store a domain budget in Redis and fetch/cache robots rules. | Static source limits. | Next for public web crawling | Redis clock/contention errors, stale robots data, upstream 429s. Fail closed for unknown robots policy where appropriate. |
| Idempotent persistence | Queue delivery is at-least-once. Keep database uniqueness constraints and use UPSERT/transactional state transitions. | Exactly-once delivery (not realistic end-to-end). | Next | Conflicting concurrent updates and partial transaction failures. |
| Checkpoint/resume and heartbeats | Operators need to distinguish a slow job from a dead worker and resume long crawls. Persist frontier cursor, counters, worker lease, and heartbeat. | Timeout-only monitoring. | After queue | Lease races, abandoned locks, inaccurate progress. |
| Backpressure and quotas | Avoid overwhelming PostgreSQL, Redis, external sites, or a single tenant when intake exceeds capacity. | Fixed worker count only. | After queue | Starvation and queue growth; publish queue age/depth alerts. |
| Prometheus, Grafana, OpenTelemetry | Make failures, latency, rates, queue age, and traces observable. | Logs only. | After queue | Cardinality explosions and noisy alerts. |
| Graceful shutdown | Stop accepting work, finish/return leased tasks, flush DB, and close clients safely during deploy. | Forced process termination. | After queue | Double processing after lease expiry; idempotency remains mandatory. |
| Proxy support | Optional for legitimate geographic/network resilience with clear source-policy compliance. | Direct egress only. | Later, only with a real requirement | Proxy bans, credential leakage, legal/policy abuse. |
| Load tests | Validate queue and persistence under controlled synthetic workload. | Ad-hoc benchmarks. | Later | Tests that do not resemble real source latency/data sizes. |

## Proposed boundaries

The API owns validation, job creation, status/read APIs, and authentication. Workers own fetch/parse/normalize/persist and emit structured events. PostgreSQL remains the source of truth for jobs, graph records, checkpoints, and failures. Redis is queue/rate-limit coordination, not the authoritative job database.

Start with a single worker process and explicit delivery semantics; scale only after metrics show a bottleneck. Do not add a graph database, Kubernetes, proxies, or multiple queues merely to make the project appear distributed.
