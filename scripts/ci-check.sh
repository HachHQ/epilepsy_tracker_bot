#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

if ! docker compose ps postgres --status running >/dev/null 2>&1; then
  echo "Starting postgres and redis..."
  docker compose up -d postgres redis
fi

NETWORK="$(docker compose ps -q postgres | xargs docker inspect --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -1)"
POSTGRES_HOST="$(docker compose ps -q postgres | xargs docker inspect --format '{{.Name}}' | sed 's#^/##')"

docker run --rm \
  --network "$NETWORK" \
  -v "$ROOT:/app" \
  -w //app \
  -e TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@${POSTGRES_HOST}:5432/diplomathesis" \
  -e API_TOKEN=ci-test-token \
  -e HMAC_SECRET_KEY=ci-test-secret \
  -e ADMINS=1 \
  -e DB_NAME=diplomathesis \
  -e DB_USER=postgres \
  -e DB_PASSWORD=postgres \
  -e DB_HOST="$POSTGRES_HOST" \
  -e DB_PORT=5432 \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  python:3.12-slim-bookworm \
  bash -c "
    apt-get update -qq &&
    apt-get install -y -qq libfreetype6 libpng16-16 >/dev/null &&
    pip install -q -r requirements.txt -r requirements-dev.txt &&
    alembic upgrade head &&
    pytest tests/ -q &&
    ruff check .
  "

echo "CI checks passed."
