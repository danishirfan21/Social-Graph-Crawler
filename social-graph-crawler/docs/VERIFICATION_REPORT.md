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

Static checks actually run for this addition:

| Command | Result |
|---|---|
| `python -m json.tool .devcontainer/devcontainer.json` | Passed. |
| `bash -n scripts/verify_codespaces.sh` | Passed. |
| `$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend\tests --no-cov` | **8 passed** at the time of the Codespaces static check. |

The Docker image was corrected to include Alembic/config/test files and to use a standard-library health check instead of the undeclared `requests` package. Compose now health-checks the backend readiness endpoint and no longer uses fixed container or network names, which makes it safer for Codespaces projects.

`docker`, `docker compose config`, and container execution were **not run** here: the Docker CLI is not installed on this Windows machine. Therefore PostgreSQL, Redis, backend container startup, migrations against a live PostgreSQL container, fixture persistence in Compose, and containerized tests remain unverified until `./scripts/verify_codespaces.sh` is run in a Codespace.

## Codespaces database-engine repair — 2026-08-21

The first Codespaces attempt built the image and started PostgreSQL and Redis, but backend startup failed before migrations with `TypeError: Invalid argument(s) 'pool_size','max_overflow' ... NullPool`.

Root cause: Compose sets `DEBUG=true`; the application used that flag to select `NullPool`, while always passing `pool_size` and `max_overflow`. `NullPool` does not accept those queue-pool options. The application now has one `create_database_engine()` path: PostgreSQL/asyncpg uses SQLAlchemy's normal `AsyncAdaptedQueuePool` with configured size, overflow, and timeout; SQLite receives only the common engine options. Alembic retains a separate short-lived `NullPool`, which is appropriate for a one-off migration process and has no pool-sizing arguments.

Actual post-fix checks run on this host:

| Command | Result |
|---|---|
| Import engine with `DATABASE_URL=postgresql+asyncpg://...` and `DEBUG=true` | Passed; reported `AsyncAdaptedQueuePool` without connecting to PostgreSQL. |
| `$env:PYTHONPATH='backend'; .\.venv\Scripts\python -m pytest backend\tests --no-cov` | **10 passed**. |
| `alembic upgrade head --sql` using PostgreSQL URL | Generated PostgreSQL migration SQL successfully; this is offline SQL generation, not a live migration. |

Docker remains unavailable in this workspace, so the repaired `./scripts/verify_codespaces.sh` has **not** been re-run here. The earlier Codespaces evidence confirms that PostgreSQL and Redis containers became healthy before the backend failure, but this report does not claim a full successful container verification. The Redis `vm.overcommit_memory` warning is a host-kernel recommendation; it is non-blocking for this small deterministic demo when Redis is healthy. It should not be changed from inside the Codespace.

## V2 implementation status — 2026-08-21

Implemented ARQ workers, PostgreSQL frontier rows with a lease/attempt/error record, fixture retry/permanent-failure/duplicate cases, source-level Redis throttle spacing, `/metrics`, and V2 job frontier/failure/resume APIs. `scripts/verify_codespaces.sh` now starts three workers and validates the V2 demo behavior.

Actual V2 checks run in this workspace: `pytest backend/tests --no-cov` (**10 passed**), `alembic upgrade head` against a clean SQLite file (including `0002_crawl_frontier`), and `bash -n scripts/verify_codespaces.sh`.

The V2 Compose workflow was not run in this Windows workspace because Docker remains unavailable. The existing Codespaces verification was for the pre-V2 baseline; this report does not claim that workers, live PostgreSQL frontier claims, Redis ARQ delivery, metrics, or V2 recovery have been container-verified yet.

## V2 worker-health repair — 2026-08-21

The first V2 Codespaces run started all three ARQ workers and connected them to Redis, while PostgreSQL, Redis, backend readiness, and Alembic `0002_crawl_frontier` also succeeded. Compose still reported workers unhealthy because they inherited the image's FastAPI HTTP healthcheck and ARQ workers do not listen on port 8000.

The worker service now overrides that inherited check. It confirms PID 1 (the ARQ process) is alive and performs a Redis `PING` using the configured broker URL. It checks every five seconds after a ten-second start period and fails after six unsuccessful checks (about 40 seconds), rather than masking a crash-loop with a long timeout. This repair has not been re-run in Codespaces from this workspace; no claim is made yet that live ARQ consumption, frontier transitions, retry, persistence, metrics, or containerized tests passed after it.

## V2 queue diagnostics repair — 2026-08-21

The next Codespaces run created the expected deduplicated frontier rows and accepted the V2 job, but the job did not reach a terminal state. The supplied evidence did not include worker task exceptions, Redis queue contents, or frontier transition rows, so no root cause is claimed from startup logs alone.

Queue tasks now carry both the committed crawl-job ID and a specific committed frontier-item ID. The API logs each ARQ task ID after commit; workers log claim, retry, completion, failure, and no-claim transitions. The verifier now dumps the job JSON, frontier rows, ARQ Redis keys, backend logs, and worker logs before failing a polling timeout. Normal Compose mode disables SQLAlchemy echo noise while retaining focused application logs. Local tests passed (**10 passed**) and the verifier shell syntax passed. This repair still requires a Codespaces rerun for live queue-to-worker verification.

## V2 verifier rerun repair — 2026-08-21

The subsequent Codespaces run reached healthy PostgreSQL, Redis, FastAPI, all three workers, migrations, health, readiness, metrics, and frontier creation, but `POST /crawl/start` returned 409 before ARQ execution. The API returns that status only for an existing active job with the same request key; the fixed verifier entity `v2-demo` therefore collides with a pending/running job left by an interrupted earlier run in the persistent PostgreSQL volume.

The verifier now creates `v2-demo-<epoch>-<shell-pid>` for every run. The fixture recognizes that prefix and produces the same deterministic success/transient/permanent/duplicate workload. This preserves active-job duplicate protection and the `(crawl_job_id, target)` frontier constraint without deleting or mutating unrelated data. A non-202 start now prints the HTTP status and response JSON before failing. This change has not yet been re-run in Codespaces, so it does not claim post-fix ARQ execution or full V2 success.
