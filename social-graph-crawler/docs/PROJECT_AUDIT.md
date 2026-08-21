# Project audit — 2026-08-21

This audit is based on source inspection and commands run in this workspace. It does not treat README text as evidence.

## Working

- FastAPI routers, SQLAlchemy graph models, and a React UI exist.
- Node CRUD includes a database uniqueness check and the node/edge tables also have uniqueness constraints.
- The three HTTP crawler classes contain real endpoint calls and persist normalized nodes/edges when their upstream responses are usable.

## Broken before this baseline repair

- There were no Alembic revision files, yet the README instructed users to migrate.
- Docker could not build reliably: its build context and `COPY backend/...` paths disagreed.
- `/api/v1/crawl/start` accepted GitHub and Wikipedia but ran only Reddit; it created one job in the API and a second job in the crawler.
- The job runner swallowed all exceptions, leaving job failures unrecorded.
- Startup created tables directly, bypassing migrations.
- The claimed Redis cache and Redis rate limiter were not connected at application lifecycle and were unused by routes/crawlers.
- Existing test directories and fixtures contained no actual test cases. The fixture additionally required an undeclared `aiosqlite` dependency.
- The frontend only loaded nodes after a crawl and intentionally discarded graph edges, so it did not render the stored graph.

## Incomplete

- External crawlers are synchronous-depth traversal with request timeouts and retry added in this baseline, but no robots.txt, pagination continuation, proxying, crawl frontier, or distributed worker exists.
- Cancellation is cooperative only at task start; it cannot interrupt an HTTP request already in progress.
- PostgreSQL and Redis cannot be exercised in this environment because Docker is not installed. `/ready` is the runtime dependency check when they are available.
- Frontend has not been built or run in this workspace as of this audit; it remains a secondary, unverified UI.

## Documented but not implemented (original README)

- Production readiness, deployment instructions, response compression, prepared statements, GIN indexes, Redis caching, Redis-backed crawler rate limiting, distributed/background reliability, tested coverage, and database performance claims.
- The stated repository URL, contact details, and license reference were placeholders or unsupported by repository contents.

## Unnecessary/dead

- `app.services.rate_limiter` remains unused by the API and should be replaced by a V2 queue/domain limiter rather than exposed as a feature.
- `db_url` argument formerly passed to the background runner was unused.
- `asyncio`, `quote`, and several imported service symbols are unused in existing source files (linting identifies the exact current set).

## Needs verification

- Compose startup, PostgreSQL migration against a clean server, Redis PING, and external API crawling require Docker/available services.
- GitHub and Reddit behavior also depends on current upstream policies/credentials; no claim is made that they ran here.
