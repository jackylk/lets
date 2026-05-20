#!/usr/bin/env bash
# Run a full local Lets website for dogfood while Railway deploys are paused.
#
# This serves the built SPA at http://127.0.0.1:8000/app and enables the
# dev-only browser login at /auth/dev/login.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOST="${LETS_HOST:-http://127.0.0.1:8000}"
HUMAN="${LETS_DEV_HUMAN:-${USER:-Neo}}"
DB_PATH="${LETS_DB_PATH:-$ROOT/lets.db}"
ARTIFACTS="${LETS_GIT_REPO:-$ROOT/.local/lets-artifacts}"

mkdir -p "$ARTIFACTS"
if [ ! -d "$ARTIFACTS/.git" ]; then
  git init "$ARTIFACTS" >/dev/null
  git -C "$ARTIFACTS" commit --allow-empty -m init >/dev/null
fi

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi

(cd frontend && npm run build)

cat <<MSG
Starting Lets local website.

Open:
  $HOST/auth/dev/login?human=$HUMAN

Then gateway login:
  LETS_HOST=$HOST .venv/bin/python -m app.gateway login

Run gateway:
  LETS_HOST=$HOST .venv/bin/python -m app.gateway run

MSG

LETS_DB_PATH="$DB_PATH" \
LETS_GIT_REPO="$ARTIFACTS" \
LETS_FRONTEND_DIST="$ROOT/frontend/dist" \
LETS_COOKIE_SECURE=false \
LETS_DEV_SESSIONS=1 \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
