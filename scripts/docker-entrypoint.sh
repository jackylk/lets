#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ] && [ -z "${LETS_DATABASE_URL:-}" ]; then
  echo "DATABASE_URL or LETS_DATABASE_URL is required for Postgres" >&2
  exit 1
fi

if [ ! -d "$LETS_GIT_REPO/.git" ]; then
  mkdir -p "$LETS_GIT_REPO"
  git -C "$LETS_GIT_REPO" init
  git -C "$LETS_GIT_REPO" config user.email "lets@local"
  git -C "$LETS_GIT_REPO" config user.name "Lets"
  git -C "$LETS_GIT_REPO" commit --allow-empty -m "init"
fi

python -m app.onboarding_reset

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
