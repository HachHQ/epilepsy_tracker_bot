# DiplomaThesis

Telegram bot for tracking epileptic seizures, medication courses, reminders, trusted contacts, and analytics.

## Stack

- Python 3.12
- aiogram 3
- PostgreSQL with async SQLAlchemy
- Redis for FSM storage and cache
- APScheduler for reminder jobs
- pandas/matplotlib for exports and charts
- Docker Compose for local/runtime deployment

## Quick Start (Docker)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. Copy `.env.example` to `.env` and fill in `API_TOKEN`, `ADMINS`, `HMAC_SECRET_KEY`.
3. Start the full stack:

```bash
docker compose up -d --build
docker compose logs -f bot
```

Migrations run automatically on bot startup. Stop everything:

```bash
docker compose down
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for proxy settings, port conflicts, and local development without Docker.

## Local Development (without Docker)

```bash
poetry install --extras dev
docker compose up -d postgres redis
poetry run alembic upgrade head
poetry run python main.py
```

On the host use `DB_HOST=localhost`, `REDIS_HOST=localhost`, and `TELEGRAM_PROXY=http://127.0.0.1:10808` if needed.

## Environment Variables

See `.env.example` for the full list. Required groups:

- Telegram bot token and admin IDs
- PostgreSQL connection settings
- Redis connection settings
- HMAC secret for signed callback payloads

`ADMINS` is parsed as a comma-separated list of Telegram user IDs, for example `123456,987654`.

## Project Layout

- `main.py` wires the bot, routers, middleware, scheduler, and notification queue.
- `handlers/` contains aiogram routers.
- `handlers_logic/` contains FSM flow helpers.
- `database/` contains SQLAlchemy models, repositories, migrations, and legacy query compatibility.
- `services/` contains cache, validation, charts, Excel import/export, and notification helpers.
- `use_cases/` contains application scenarios that are testable without Telegram API calls.
- `tests/` contains automated tests.
- `docker-compose.yml` runs PostgreSQL, Redis, and the bot.

## Quality Checks

```bash
docker compose up -d postgres redis
bash scripts/ci-check.sh
```

Or manually:

```bash
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
pytest tests/ -q
ruff check tests scripts
```

CI runs on every push/PR to `master` (see `.github/workflows/ci.yml`).

Architecture plans: [ROADMAP.md](ROADMAP.md). Git workflow: [RULE.md](RULE.md).

The codebase follows thin handlers → use cases → repositories. Prefer that structure for new features.
