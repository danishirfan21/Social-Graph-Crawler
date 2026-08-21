# Social Graph Crawler

A FastAPI service that stores a small relationship graph in PostgreSQL. It can ingest public-source data from Reddit, GitHub, and Wikipedia, and includes a deterministic `fixture` source so the full local pipeline can be exercised without credentials or network access.

## Current architecture

`React UI -> FastAPI -> PostgreSQL` with Redis as a connectivity-checked cache client. Crawl work is currently executed by FastAPI `BackgroundTasks` in the same process: this is suitable only for local development and is explicitly not a durable distributed worker system.

The verified pipeline is: `POST job -> fixture fetch/parse -> normalization -> PostgreSQL nodes and edges -> completed/failed job retrieval`.

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

## Start a local crawl

The fixture source is deterministic and requires no credentials:

```bash
curl -X POST http://localhost:8000/api/v1/crawl/start \
  -H "Content-Type: application/json" \
  -d '{"source":"fixture","start_entity":"Python","depth":2,"max_entities":10}'
```

Use the returned `id` with `GET /api/v1/crawl/jobs/{id}`. `start_entity: "fail"` is a deterministic error path that records a failed job. Use `GET /api/v1/nodes/` and `GET /api/v1/edges/` to inspect persisted graph data.

GitHub, Reddit, and Wikipedia sources make real HTTP calls. GitHub/Reddit credentials are optional but may be needed for practical rate limits; their current upstream behavior has not been verified in this repository.

## Testing

```powershell
$env:PYTHONPATH = 'backend'
.\.venv\Scripts\python -m pytest backend\tests --no-cov
```

Tests cover health, node duplicate rejection, deterministic crawl persistence, duplicate graph records, job status, and recorded failure. See [the verification report](docs/VERIFICATION_REPORT.md) for commands actually executed.

## Limitations and next steps

- The frontend has not yet been integrated to render persisted edges.
- The local background runner loses in-flight work if the API process stops.
- There is no robots.txt policy, crawl frontier, checkpointing, worker heartbeat, or proxy support.
- Redis is connected and used by the readiness check, but caching and API throttling are not yet product features.

The proposed path from this trustworthy local baseline to a worker-based crawler platform is in [docs/V2_ARCHITECTURE_PLAN.md](docs/V2_ARCHITECTURE_PLAN.md).
