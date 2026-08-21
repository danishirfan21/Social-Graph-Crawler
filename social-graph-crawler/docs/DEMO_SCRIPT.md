# 2–4 minute portfolio demo

## 0:00–0:30 — architecture

Open the README diagram. Say: “FastAPI persists jobs and frontier rows in PostgreSQL, Redis/ARQ distributes committed work, and independently scalable workers update the frontier and graph records.”

## 0:30–1:00 — stack

```bash
docker compose ps
```

Point out the API, PostgreSQL, Redis, and three healthy worker containers.

## 1:00–1:30 — submit deterministic work

```bash
curl -X POST http://localhost:8000/api/v1/crawl/start \
  -H 'Content-Type: application/json' \
  -d '{"source":"fixture","start_entity":"v2-demo-recording","depth":2,"max_entities":10}'
```

Copy the returned job ID into `JOB_ID`.

## 1:30–2:15 — show durable state

```bash
curl http://localhost:8000/api/v1/crawl/jobs/$JOB_ID/frontier
curl http://localhost:8000/api/v1/crawl/jobs/$JOB_ID/failures
```

Point out one successful attempt, the transient item reaching attempt three, one permanent failed item, and only one `duplicate` frontier row.

## 2:15–2:45 — observability and finalization

```bash
curl http://localhost:8000/api/v1/crawl/jobs/$JOB_ID
curl http://localhost:8000/metrics/ | grep crawler_
```

Explain that permanent child failure does not leave the parent job running once all work is terminal.

## 2:45–3:15 — reproducibility

```bash
./scripts/verify_codespaces.sh
```

Show the actual successful `V2 VERIFY SUCCEEDED` output from a prior run; do not manufacture it. For screenshots, capture: README diagram, `docker compose ps`, frontier JSON, and `/metrics/`.
