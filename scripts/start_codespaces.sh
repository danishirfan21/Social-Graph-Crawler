#!/usr/bin/env bash
# Start a durable no-Docker Codespaces runtime. Safe to run repeatedly.
set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
runtime_dir="$root_dir/.runtime"
mkdir -p "$runtime_dir"

if ! command -v redis-server >/dev/null 2>&1 || [[ ! -x "$root_dir/.venv/bin/uvicorn" ]]; then
  echo "Runtime dependencies are missing; run scripts/bootstrap_codespaces.sh first." >&2
  exit 1
fi

redis-cli ping >/dev/null 2>&1 || redis-server --daemonize yes

export DATABASE_URL="sqlite+aiosqlite:////workspaces/Social-Graph-Crawler/social_graph_v2.db"
export REDIS_URL="redis://localhost:6379/0"

(cd "$root_dir/backend" && "$root_dir/.venv/bin/alembic" upgrade head)

start_if_absent() {
  local pattern="$1"
  local log_file="$2"
  shift 2
  if ! pgrep -f "$pattern" >/dev/null 2>&1; then
    nohup "$@" >"$log_file" 2>&1 &
  fi
}

start_if_absent "uvicorn app.main:app.*--port 8000" "$runtime_dir/api.log" \
  env DATABASE_URL="$DATABASE_URL" REDIS_URL="$REDIS_URL" "$root_dir/.venv/bin/uvicorn" app.main:app --app-dir "$root_dir/backend" --host 0.0.0.0 --port 8000
start_if_absent "arq app.worker.WorkerSettings" "$runtime_dir/worker.log" \
  env DATABASE_URL="$DATABASE_URL" REDIS_URL="$REDIS_URL" "$root_dir/.venv/bin/arq" app.worker.WorkerSettings
start_if_absent "react-scripts start" "$runtime_dir/frontend.log" \
  env BROWSER=none REACT_APP_API_URL=/api/v1 npm --prefix "$root_dir/frontend" start

echo "Codespaces runtime started: frontend :3000, API :8000."
