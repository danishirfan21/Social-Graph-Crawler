#!/usr/bin/env bash
# Verify the complete Compose stack from a GitHub Codespace or another Linux host.
set -euo pipefail

compose() { docker compose "$@"; }
fail() { echo "VERIFY FAILED: $*" >&2; exit 1; }

diagnose_job() {
  [[ -n "${job_id:-}" ]] || return 0
  echo "V2 diagnostic: job ${job_id}" >&2
  curl --silent "http://localhost:8000/api/v1/crawl/jobs/${job_id}" >&2 || true
  curl --silent "http://localhost:8000/api/v1/crawl/jobs/${job_id}/frontier" >&2 || true
  compose exec -T redis redis-cli --scan --pattern 'arq:*' >&2 || true
  compose logs --no-color backend worker >&2 || true
}

command -v docker >/dev/null || fail "Docker is not installed or not on PATH."
docker compose version >/dev/null || fail "Docker Compose v2 is unavailable."
command -v curl >/dev/null || fail "curl is required."
command -v python3 >/dev/null || fail "python3 is required."

cleanup() {
  status=$?
  if [[ $status -ne 0 ]]; then
    echo "Container logs after failure:" >&2
    compose logs --no-color >&2 || true
  fi
  exit "$status"
}
trap cleanup EXIT

echo "Starting PostgreSQL, Redis, FastAPI, and three workers..."
compose up --build --detach --wait --scale worker=3

echo "Applying Alembic migrations..."
compose exec -T backend alembic upgrade head

echo "Checking API health and readiness..."
curl --fail --silent --show-error http://localhost:8000/health >/dev/null
curl --fail --silent --show-error http://localhost:8000/ready >/dev/null
curl --location --fail --silent --show-error http://localhost:8000/metrics >/dev/null

verification_run="v2-demo-$(date +%s)-$$"
echo "Starting deterministic V2 fixture crawl: ${verification_run}"
start_response=$(curl --silent --show-error -w '\n%{http_code}' \
  -X POST http://localhost:8000/api/v1/crawl/start \
  -H 'Content-Type: application/json' \
  --data "{\"source\":\"fixture\",\"start_entity\":\"${verification_run}\",\"depth\":2,\"max_entities\":10}")
start_status=$(tail -n 1 <<<"$start_response")
job_json=$(sed '$d' <<<"$start_response")
if [[ "$start_status" != "202" ]]; then
  echo "Start crawl failed: HTTP ${start_status}" >&2
  echo "$job_json" >&2
  fail "Unable to create verification crawl."
fi
job_id=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])' <<<"$job_json")

for _ in $(seq 1 30); do
  job_json=$(curl --fail --silent --show-error "http://localhost:8000/api/v1/crawl/jobs/${job_id}")
  job_status=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])' <<<"$job_json")
  if [[ "$job_status" == "completed" ]]; then
    break
  fi
  [[ "$job_status" == "failed" ]] && fail "Fixture crawl failed: $job_json"
  sleep 1
done
if [[ "$job_status" != "completed" ]]; then
  diagnose_job
  fail "Fixture crawl did not finish within 30 seconds."
fi

frontier_json=$(curl --fail --silent --show-error "http://localhost:8000/api/v1/crawl/jobs/${job_id}/frontier")
python3 -c 'import json,sys; x=json.load(sys.stdin); assert len(x)==4; assert sum(i["status"]=="completed" for i in x)==3; assert sum(i["status"]=="failed" for i in x)==1; assert next(i for i in x if i["target"]=="transient")["attempt_count"]==3' <<<"$frontier_json" || fail "Frontier, duplicate protection, retry, or permanent failure verification failed."

echo "Verifying PostgreSQL persistence..."
node_count=$(compose exec -T postgres psql -U postgres -d social_graph -tAc "SELECT count(*) FROM nodes WHERE source = 'fixture';")
edge_count=$(compose exec -T postgres psql -U postgres -d social_graph -tAc "SELECT count(*) FROM edges WHERE relationship_type = 'mentions';")
if (( node_count < 2 )); then
  fail "Expected at least two fixture nodes; found $node_count."
fi
if (( edge_count < 1 )); then
  fail "Expected at least one fixture edge; found $edge_count."
fi

echo "Running backend test suite in the backend container..."
compose exec -T backend pytest

echo "V2 VERIFY SUCCEEDED:"
echo "API PostgreSQL Redis workers migrations crawl-frontier fixture-retry duplicate-protection persistence metrics tests"
echo "Stop the stack with: docker compose down"
