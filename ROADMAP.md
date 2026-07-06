# Architecture Roadmap

План развития архитектуры Telegram-бота для учёта эпилептических приступов.

Текущая целевая схема (см. также `RULE.md`):

```
handlers / handlers_logic
        ↓
   use_cases
        ↓
repositories → PostgreSQL
        ↓
redis_cache / invalidation

adapters/telegram — доставка в Telegram (фото, документы, очередь уведомлений)
services/         — чистая логика (графики, excel, validators, cache keys)
i18n + locales/   — все пользовательские тексты
```

## Статус на сейчас

| Область | Готово | В работе / долг |
|---------|--------|-----------------|
| Retention (soft delete, purge) | ✅ | — |
| i18n foundation (`locales/ru`) | ✅ | `locales/en`, user locale setting |
| use_cases | users, profiles, seizures, retention, medications, notifications, trusted | — |
| repositories | users, profiles, seizures, retention, medications, notifications, trusted | import_export |
| `orm_query.py` (~560 строк) | частично заменён | вычистить |
| CI (GitHub Actions) | ✅ | ruff на весь проект |
| Толстые handlers | — | control_panel, medication, notification |

---

## Трек 1 — Слоистая архитектура (приоритет: высокий)

**Цель:** handlers только оркестрируют Telegram; бизнес-логика — в use cases.

### Шаги

1. **Repositories** для `medication`, `notifications`, `trusted_persons`, `import_export`.
2. **Use cases** с теми же границами; инвалидация кэша только из use cases.
3. **Похудеть handlers:** `trusted_person_handlers`, `import_export_handlers`, `medication_handlers`, `notification_handlers` — убрать прямые вызовы `orm_*`.
4. **Удалить `orm_query.py`** когда все вызовы переедут в repositories.

### Критерий готовности

- В `handlers/` нет импортов из `database.orm_query`.
- Каждый сценарий покрыт unit-тестом use case.

### Ветки

- `refactor/medication-use-cases`
- `refactor/notifications-use-cases`
- `refactor/trusted-persons-use-cases`

---

## Трек 2 — FSM и сценарий приступа (приоритет: средний)

**Проблема:** `handlers_logic/seizure_form_logic.py` (~670 строк) смешивает шаги формы, валидацию и ответы.

### Шаги

1. ✅ Валидация — только `services/validators.py`.
2. ✅ Каждый шаг FSM → тонкий handler + `use_cases/seizures`.
3. ✅ Общий рендер превью приступа — `adapters/telegram/delivery.py` (`show_seizure_preview`).
4. ✅ `handlers_logic/seizure_form/` — модули по шагам; `seizure_form_logic.py` — re-export.

### Критерий готовности

- ✅ `seizure_form_logic.py` < 300 строк (разбит на модули).
- ✅ Тесты use case без aiogram.

---

## Трек 3 — Завершение i18n (приоритет: средний, низкая трудоёмкость)

### Осталось

| Что | Файл |
|-----|------|
| Заголовки колонок Excel | ✅ `locales/ru/excel.yaml` |
| Английская локаль | `locales/en/` |
| Локаль по настройке пользователя | `User` + middleware |
| Guard от кириллицы в handlers | ✅ `tests/test_i18n_guard.py` |

### Ветка

- `feature/i18n-en-and-excel`

---

## Трек 4 — Adapters vs services (приоритет: средний)

**Цель:** Telegram-специфика только в `adapters/telegram/`.

### Шаги

1. Убрать прокладки `services/notification_queue.py`, `services/medication_reminders.py` (импорты напрямую из adapters).
2. Analytics: `use_cases/analytics.py` + `services/charts/` вместо прямых вызовов из handlers.

---

## Трек 5 — Кэш и консистентность (приоритет: средний)

1. Таблица «событие → ключи Redis» в `services/cache_keys.py`.
2. Инвалидация только из use cases.
3. Расширить `tests/test_cache_invalidation.py`.

---

## Трек 6 — Инженерная зрелость (приоритет: высокий, **наименьшая трудоёмкость**)

> **Старт реализации:** этот трек.

### Шаги

- [x] `requirements-dev.txt` — pytest, ruff
- [x] `.github/workflows/ci.yml` — тесты, alembic, docker build, ruff
- [x] `scripts/ci-check.sh` — локальный прогон как в CI
- [x] `print` → `logging` / удаление debug-print в handlers
- [x] healthcheck для `bot` в `docker-compose.yml`
- [x] badge CI в `README.md`
- [ ] `ruff check .` на весь проект (сейчас только `tests/` и `scripts/`)

### Локальная проверка

```bash
# Postgres + Redis должны быть запущены
docker compose up -d postgres redis
bash scripts/ci-check.sh
```

Или вручную:

```bash
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
pytest tests/ -q
ruff check .
docker build -t diplomathesis-bot:local .
```

---

## Трек 7 — Доменные фичи (после треков 1–2)

| Фича | Зависимость |
|------|-------------|
| Audit log удалений | repositories + use_cases |
| Webhook вместо polling | `main.py`, adapters |
| RBAC доверенных лиц | trusted_persons use case |
| Prometheus metrics | middleware |

---

## Рекомендуемый порядок итераций

### Итерация A (текущая)

1. ✅ i18n foundation (PR #2)
2. ✅ **Трек 6 — CI** (PR #3)
3. ✅ Трек 3 — Excel + i18n guard
4. ✅ Трек 1 — medication use cases
5. ✅ Трек 1 — notifications use cases
6. ✅ Трек 1 — trusted persons use cases

### Итерация B

7. ✅ Трек 2 — FSM приступа (начало)
8. ✅ Трек 1 — вычистка `control_panel_handlers`
9. ✅ Трек 2 — journal edit flow

### Итерация C

10. Трек 1 — удаление `orm_query.py`
11. Трек 5 — cache contract

---

## Метрики для диплома (до / после)

| Метрика | Как измерить |
|---------|--------------|
| Coupling handlers → DB | `rg "orm_query\|orm_" handlers/` |
| Размер крупнейших файлов | `wc -l handlers/*.py` |
| Покрытие тестами | `pytest --co -q` |
| Время CI | GitHub Actions |

---

## Связанные документы

- [RULE.md](RULE.md) — Git workflow, правила для AI
- [README.md](README.md) — запуск и стек
- [CONTRIBUTING.md](CONTRIBUTING.md) — локальная разработка
