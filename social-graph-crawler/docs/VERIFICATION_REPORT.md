# Verification report — 2026-08-21

## Executed successfully

| Command | Result |
|---|---|
| `python -m venv .venv` | Created local test environment. |
| `python -m pip install` (backend runtime/test dependencies) | Installed enough pinned dependencies to run FastAPI, Alembic, and tests. |
| `$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend\tests --no-cov` | **7 passed**. Exercises health, node duplicate behavior, deterministic crawl persistence, duplicate graph records, failure recording, and API job lifecycle. |
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
