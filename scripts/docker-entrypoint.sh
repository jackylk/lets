#!/bin/sh
set -eu

mkdir -p "$(dirname "$LETS_DB_PATH")"

if [ ! -d "$LETS_GIT_REPO/.git" ]; then
  mkdir -p "$LETS_GIT_REPO"
  git -C "$LETS_GIT_REPO" init
  git -C "$LETS_GIT_REPO" config user.email "lets@local"
  git -C "$LETS_GIT_REPO" config user.name "Lets"
  git -C "$LETS_GIT_REPO" commit --allow-empty -m "init"
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
