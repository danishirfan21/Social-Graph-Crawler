#!/usr/bin/env bash
# Verify the complete Compose stack from a GitHub Codespace or another Linux host.
set -euo pipefail

compose() { docker compose "$@"; }
fail() { echo "VERIFY FAILED: $*" >&2; exit 1; }

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

echo "Starting PostgreSQL, Redis, and FastAPI..."
compose up --build --detach --wait

echo "Applying Alembic migrations..."
compose exec -T backend alembic upgrade head

echo "Checking API health and readiness..."
curl --fail --silent --show-error http://localhost:8000/health >/dev/null
curl --fail --silent --show-error http://localhost:8000/ready >/dev/null

echo "Starting deterministic fixture crawl..."
job_json=$(curl --fail --silent --show-error \
  -X POST http://localhost:8000/api/v1/crawl/start \
  -H 'Content-Type: application/json' \
  --data '{"source":"fixture","start_entity":"Codespaces Demo","depth":2,"max_entities":10}')
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
[[ "$job_status" == "completed" ]] || fail "Fixture crawl did not finish within 30 seconds."

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

echo "VERIFY SUCCEEDED: API, PostgreSQL, Redis, migrations, fixture crawl, persistence, and tests passed."
echo "Stop the stack with: docker compose down"
