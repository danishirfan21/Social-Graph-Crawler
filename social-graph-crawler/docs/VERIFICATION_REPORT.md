# Verification report — 2026-08-21

## Executed successfully

| Command | Result |
|---|---|
| `python -m venv .venv` | Created local test environment. |
| `python -m pip install` (backend runtime/test dependencies) | Installed enough pinned dependencies to run FastAPI, Alembic, and tests. |
| `cd backend; $env:PYTHONPATH='.'; ..\.venv\Scripts\python -m pytest` | **8 passed**. Exercises health, node duplicate behavior, deterministic crawl persistence, duplicate graph records, failure recording, reruns after completion, and API job lifecycle. |
| `DATABASE_URL=sqlite+aiosqlite:///./migration-check.db; alembic upgrade head` | Succeeded from a clean SQLite file as a migration smoke test. |
| `uvicorn app.main:app --host 127.0.0.1 --port 8010` with the migrated SQLite database | Started successfully; `GET /health` returned healthy JSON and `GET /docs` returned HTTP 200. |
| `alembic upgrade head --sql` with PostgreSQL URL | Generated PostgreSQL migration SQL successfully; no database connection was made by this offline command. |

## Attempted but not executable in this environment

| Check | Result |
|---|---|
| `docker compose config`, Docker Compose startup, PostgreSQL startup, Redis startup | Docker CLI is not installed (`docker` command not found). Not tested. |
| Clean PostgreSQL migration | Not tested: no PostgreSQL service is available. SQLite migration smoke test passed, but it is not a substitute for PostgreSQL. |
| `/ready`, `/docs` through a live Uvicorn server | Not tested against real PostgreSQL/Redis because those services are unavailable. `/health` is tested through ASGI. |
| Real GitHub/Reddit/Wikipedia crawls | Not tested. Fixture crawl is deterministic and tested; external sources make live HTTP calls and may need credentials/rate-limit handling. |
| Frontend build/integration | Not tested. |
| Ruff/Black | Not run. The original pinned lint packages could not be installed within the available network time; this report intentionally does not claim lint success. |

No coverage percentage, performance number, Docker success, or live external API success is claimed.

## Codespaces and container verification — 2026-08-21

Added `.devcontainer/devcontainer.json` using the official Docker-in-Docker devcontainer feature and forwarding 8000, 5432, and 6379. Added `scripts/verify_codespaces.sh`, which starts Compose, waits for health checks, runs Alembic, checks `/health` and `/ready`, runs the fixture job, queries PostgreSQL directly, and runs tests inside the backend container.

The Docker image was corrected to include Alembic/config/test files and to use a standard-library health check instead of the undeclared `requests` package. Compose now health-checks the backend readiness endpoint and no longer uses fixed container or network names, which makes it safer for Codespaces projects.

`docker`, `docker compose config`, and container execution were **not run** here: the Docker CLI is not installed on this Windows machine. Therefore PostgreSQL, Redis, backend container startup, migrations against a live PostgreSQL container, fixture persistence in Compose, and containerized tests remain unverified until `./scripts/verify_codespaces.sh` is run in a Codespace.
