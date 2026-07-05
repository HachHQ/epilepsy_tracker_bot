#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python - <<'PY'
import asyncio
import os
import sys

import asyncpg


async def main() -> None:
    await asyncpg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
    )


try:
    asyncio.run(main())
except Exception:
    sys.exit(1)
PY
do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Running migrations..."
alembic upgrade head

echo "Running seed..."
python -m database.seed

echo "Starting bot..."
exec "$@"
