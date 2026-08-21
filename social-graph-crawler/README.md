# Social Graph Crawler

A FastAPI service that stores a small relationship graph in PostgreSQL. It can ingest public-source data from Reddit, GitHub, and Wikipedia, and includes a deterministic `fixture` source so the full local pipeline can be exercised without credentials or network access.

## V2 architecture

```text
                 FastAPI
                    |
              Redis / ARQ queue
                    |
       +------------+------------+
       |            |            |
    Worker 1     Worker 2     Worker 3
       +------------+------------+
                    |
      PostgreSQL frontier -> nodes / edges
                    |
           Prometheus /metrics
```

FastAPI persists a job and deduplicated frontier items, then enqueues compact ARQ tasks. Workers claim PostgreSQL frontier rows with leases, process deterministic fixture cases, and persist idempotent graph records. Redis coordinates task delivery and source-level throttle spacing. This is at-least-once processing, not exactly-once delivery.

## Technologies

Python 3.11+, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis, aiohttp, pytest; React and D3 are included as an unverified frontend.

## Local setup

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -r backend\requirements.txt
   ```

2. Copy `.env.example` to `.env` and start PostgreSQL and Redis. The default local URLs are in that file.

3. Apply migrations and start the API:

   ```powershell
   cd backend
   ..\.venv\Scripts\alembic upgrade head
   ..\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

`GET /health` reports process health. `GET /ready` returns 200 only when both PostgreSQL and Redis are reachable. Open `http://127.0.0.1:8000/docs` for the generated API documentation.

## Docker

With Docker Desktop installed:

```bash
docker compose up --build
docker compose ps
curl http://localhost:8000/ready
```

The backend container applies `alembic upgrade head` before starting Uvicorn. No Docker command was available in the audit environment, so this Compose path remains to be verified there.

## Run in GitHub Codespaces

1. On GitHub, choose **Code → Codespaces → Create codespace**.
2. Wait for the development container to finish starting.
3. Run one command from the repository root:

   ```bash
   ./scripts/verify_codespaces.sh
   ```

It builds and starts PostgreSQL, Redis, FastAPI, and three workers; runs migrations; executes a deterministic fixture crawl with retry/failure cases; checks PostgreSQL persistence and metrics; and runs backend tests. A successful run ends with `V2 VERIFY SUCCEEDED`.

Codespaces forwards FastAPI on port 8000 (open the forwarded URL with `/docs` for Swagger). PostgreSQL (5432) and Redis (6379) are also forwarded for optional inspection. Stop the stack with:

```bash
docker compose down
```

The frontend is not included in Compose: it has not been built or verified and currently does not render persisted edges. The backend pipeline is the supported Codespaces verification path.

## V2 crawl demo

The fixture source is deterministic and requires no credentials:

```bash
curl -X POST http://localhost:8000/api/v1/crawl/start \
  -H "Content-Type: application/json" \
  -d '{"source":"fixture","start_entity":"v2-demo","depth":2,"max_entities":10}'
```

Use the returned `id` with `GET /api/v1/crawl/jobs/{id}`, `/frontier`, and `/failures`. `v2-demo` has three completed items, one permanently failed item, a deduplicated discovery, and a transient item that succeeds on attempt three. `slow-demo` is suitable for the worker-restart demonstration below.

Scale workers with `docker compose up --scale worker=3`. To demonstrate lease recovery, start `slow-demo`, stop one worker with `docker compose stop worker`, wait longer than `FRONTIER_LEASE_SECONDS`, then restart it with `docker compose start worker` and call `POST /api/v1/crawl/jobs/{id}/resume`.

GitHub, Reddit, and Wikipedia sources make real HTTP calls. GitHub/Reddit credentials are optional but may be needed for practical rate limits; their current upstream behavior has not been verified in this repository.

## Testing

```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python -m pytest backend\tests --no-cov
```

Tests cover API submission, frontier deduplication, retries, permanent failure recording, idempotent graph persistence, and engine configuration. See [the verification report](docs/VERIFICATION_REPORT.md) for commands actually executed.

## Limitations and next steps

- The frontend has not yet been integrated to render persisted edges.
- External crawlers are not yet adapted to the durable frontier; V2 verification is fixture-only.
- Lease recovery is at-least-once and requires the resume endpoint or a worker claim cycle; it is not automatic consensus.
- There is no robots.txt policy, proxy support, Grafana, or frontend graph integration.

The proposed path from this trustworthy local baseline to a worker-based crawler platform is in [docs/V2_ARCHITECTURE_PLAN.md](docs/V2_ARCHITECTURE_PLAN.md).
