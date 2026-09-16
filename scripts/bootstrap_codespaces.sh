#!/usr/bin/env bash
# Install the no-Docker runtime used by this project's Codespaces fallback.
set -euo pipefail

root_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if ! command -v redis-server >/dev/null 2>&1 || ! command -v node >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y redis-server nodejs npm
  elif command -v apk >/dev/null 2>&1; then
    sudo apk add --no-cache redis nodejs npm
  else
    echo "Install Redis and Node.js 20+ before starting the no-Docker runtime." >&2
    exit 1
  fi
fi

if [[ ! -x "$root_dir/.venv/bin/python" ]]; then
  python3 -m venv "$root_dir/.venv"
fi
"$root_dir/.venv/bin/pip" install --upgrade pip
"$root_dir/.venv/bin/pip" install -r "$root_dir/backend/requirements.txt"

if [[ ! -d "$root_dir/frontend/node_modules" ]]; then
  (cd "$root_dir/frontend" && npm ci)
fi
