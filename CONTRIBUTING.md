# Contributing

## Локальный запуск

### Рекомендуемый способ — полный Docker Compose

PostgreSQL, Redis и бот работают в контейнерах. Нужны только Docker Desktop и файл `.env`.

```powershell
cd D:\Programming\DiplomaThesis
copy .env.example .env
# заполните API_TOKEN, ADMINS, HMAC_SECRET_KEY

docker compose up -d --build
docker compose logs -f bot
```

Остановка:

```bash
docker compose down
```

Полный сброс данных (БД, Redis, временные графики):

```bash
docker compose down -v
docker compose up -d --build
```

---

## Docker Compose

### Сервисы

| Сервис | Образ / сборка | Назначение |
|--------|----------------|------------|
| `postgres` | `postgres:14-alpine` | основная БД |
| `redis` | `redis:7-alpine` | FSM aiogram + кэш |
| `bot` | `Dockerfile` | Telegram-бот |

### Что происходит при старте `bot`

1. Ожидание готовности PostgreSQL.
2. `alembic upgrade head` (идемпотентно).
3. `python main.py` — polling.

### Команды

```bash
docker compose up -d --build    # собрать и запустить всё
docker compose ps               # статус
docker compose logs -f bot      # логи бота
docker compose restart bot      # перезапуск только бота
docker compose build bot        # пересборка после изменений кода
docker compose up -d bot        # применить новый образ
```

Миграции вручную (обычно не нужно):

```bash
docker compose run --rm --no-deps bot alembic upgrade head
```

### Переменные окружения в Docker

Файл `.env` монтируется через `env_file`. В `docker-compose.yml` для контейнера `bot` переопределяются:

```env
DB_HOST=postgres
REDIS_HOST=redis
TELEGRAM_PROXY=http://host.docker.internal:10808
```

`host.docker.internal` — адрес Windows/macOS-хоста из контейнера (для прокси Telegram).

На хосте (без Docker) используйте:

```env
DB_HOST=localhost
REDIS_HOST=localhost
TELEGRAM_PROXY=http://127.0.0.1:10808
```

### Прокси Telegram

| Где запущен бот | `TELEGRAM_PROXY` |
|-----------------|------------------|
| Docker | `http://host.docker.internal:10808` |
| Windows / Poetry | `http://127.0.0.1:10808` |

Если прокси не нужен — закомментируйте или удалите `TELEGRAM_PROXY` в `.env`.

### Порты на хосте

По умолчанию пробрасываются:

- PostgreSQL: `${DB_PORT:-5432}`
- Redis: `${REDIS_PORT:-6379}`

Бот наружу порты не публикует (long polling).

При конфликте портов остановите Windows PostgreSQL / WSL Redis или смените порты в `.env`:

```env
DB_PORT=5433
REDIS_PORT=6380
```

### Volumes

| Volume | Содержимое |
|--------|------------|
| `pgdata` | данные PostgreSQL |
| `redisdata` | данные Redis (AOF) |
| `bot_temp_images` | PNG-графики аналитики |

---

## Разработка без Docker (только бот на хосте)

Инфраструктура в Docker, код запускается через Poetry — удобно при частых правках:

```bash
docker compose up -d postgres redis
poetry install --extras dev
poetry run alembic upgrade head
poetry run python main.py
```

В `.env` для этого режима: `DB_HOST=localhost`, `REDIS_HOST=localhost`.

---

## Python и зависимости (для dev на хосте)

```powershell
poetry env use C:\Path\To\Python312\python.exe
set POETRY_VIRTUALENVS_IN_PROJECT=false
set NO_PROXY=*
poetry install --extras dev
poetry run pytest -q
```

---

## Настройка `.env`

```powershell
copy .env.example .env
```

Обязательные переменные:

```env
API_TOKEN=...
ADMINS=123456789
HMAC_SECRET_KEY=...

DB_NAME=diplomathesis
DB_USER=postgres
DB_PASSWORD=postgres

REDIS_DB=0
```

`.env` в git не коммитится.

---

## Миграции

Единая цепочка миграций: `20260527_0001` → legacy no-op → **`bc9ff2e0ce8b` (head)**. Используйте `alembic upgrade head`.

В Docker миграции применяются автоматически в `docker/entrypoint.sh`.

### Dev seed

При старте контейнера `bot` выполняется `python -m database.seed` — **идемпотентно** создаёт пользователя, если его ещё нет:

| Поле | Значение по умолчанию |
|------|------------------------|
| `telegram_id` | `466024868` |
| `login` | `arthur` |
| `name` | `Arthur` |
| `timezone` | `+7` |
| кодовое слово | `devseed123` |
| профиль | `Основной` |

Переопределение через `.env`: `SEED_TELEGRAM_ID`, `SEED_LOGIN`, `SEED_NAME`, `SEED_TIMEZONE`, `SEED_KEYWORD`, `SEED_PROFILE_NAME`.

Вручную:

```bash
docker compose exec bot python -m database.seed
poetry run python -m database.seed
```

Убедитесь, что ваш Telegram ID указан в `ADMINS` в `.env`, если нужны админ-команды.

При ошибке `тип "requeststatus" уже существует`:

```bash
docker compose down -v
docker compose up -d --build
```

---

## Типичные проблемы

| Симптом | Решение |
|---------|---------|
| `port is already allocated` | Освободите порт или смените `DB_PORT` / `REDIS_PORT` |
| `Cannot connect to host api.telegram.org` | Задайте `TELEGRAM_PROXY` (см. таблицу выше) |
| `Conflict: only one bot instance` | Остановите второй процесс: `docker compose stop bot` и убейте `python main.py` на хосте |
| Изменения кода не применились | `docker compose build bot && docker compose up -d bot` |
| `env_file .env not found` | Создайте `.env` из `.env.example` |

---

## Development Workflow

1. Keep changes small and tied to one domain or scenario.
2. Run `ruff check .` and `pytest` before committing.
3. Add or update tests for changed business logic.
4. Add an Alembic migration for every schema change.

## Architecture Rules

- Handlers should only translate Telegram events into use case calls and send responses.
- Use cases own scenario decisions, validation orchestration, cache invalidation, and repository calls.
- Repositories own SQLAlchemy queries and should not import aiogram objects.
- Cache helpers own Redis keys and serialization formats.
- Formatters/keyboards own Telegram presentation.

## Database Changes

Do not rely on `Base.metadata.create_all` for schema evolution. Create migrations with:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Review generated migrations before running them.

## Tests

```bash
poetry run pytest
poetry run ruff check .
poetry run mypy .
```
