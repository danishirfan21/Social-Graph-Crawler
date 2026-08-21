# Portfolio copy

## One line

Distributed crawling and data-ingestion system using FastAPI, PostgreSQL, Redis, and ARQ workers.

## Resume bullets

- Built a containerized distributed crawling pipeline with FastAPI, PostgreSQL frontier persistence, Redis/ARQ workers, and independently scalable worker containers.
- Implemented durable work claiming, lease-based recovery, retry/backoff, database-backed deduplication, permanent failure tracking, and at-least-once/idempotent processing semantics.
- Created deterministic failure fixtures and a GitHub Codespaces verifier covering queue delivery, three workers, PostgreSQL persistence, Prometheus metrics, and 11 containerized tests.

## LinkedIn/project description

Built a distributed crawler portfolio project that persists crawl jobs and frontier state in PostgreSQL, distributes committed work through Redis/ARQ, and processes it with scalable workers. The demo covers retries, duplicate prevention, permanent failures, parent finalization, metrics, and reproducible Codespaces verification.

## 30-second introduction

“I built this to show the reliability side of crawling, not just HTTP fetching. FastAPI persists a crawl job and a PostgreSQL frontier, Redis/ARQ distributes committed items to workers, and the workers persist retries, failures, and graph data. I deliberately use at-least-once delivery with database constraints and idempotent writes. The fixture demo proves retries, duplicate prevention, permanent failure handling, and finalization in Docker Compose.”
