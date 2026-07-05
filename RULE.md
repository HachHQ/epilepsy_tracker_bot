# Правила работы с Git

Этот репозиторий живёт на GitHub. Все изменения в основную ветку (`master`) вносятся **через Pull Request** из отдельной ветки — даже если работает один человек.

## Основная ветка

- **`master`** — стабильная, деплоится/запускается в Docker, всегда должна быть рабочей.
- Прямой push в `master` — только для срочных hotfix, когда PR физически невозможен. В обычном режиме — не использовать.

## Workflow: одна задача = одна ветка = один PR

```bash
# 1. Обновить основную ветку
git checkout master
git pull origin master

# 2. Создать ветку под задачу
git checkout -b feature/short-description

# 3. Работа, коммиты
git add ...
git commit -m "Краткое описание зачем, а не что"

# 4. Запушить ветку
git push -u origin feature/short-description

# 5. На GitHub: Pull requests → New pull request
#    base: master  ←  compare: feature/short-description

# 6. После merge — подтянуть master и удалить локальную ветку
git checkout master
git pull origin master
git branch -d feature/short-description
```

На GitHub **Pull Request (PR)** — аналог Merge Request в GitLab.

## Именование веток

| Префикс | Когда использовать | Пример |
|---------|-------------------|--------|
| `feature/` | новая функциональность | `feature/profile-restore` |
| `fix/` | исправление бага | `fix/docker-entrypoint-crlf` |
| `refactor/` | рефакторинг без смены поведения | `refactor/seizure-use-cases` |
| `chore/` | инфра, deps, CI, docs | `chore/github-actions` |
| `test/` | только тесты | `test/integration-retention` |

Имя короткое, через дефис, на английском.

## Коммиты

- Одна логическая правка — один коммит (или серия связанных коммитов в одном PR).
- Сообщение — **зачем** изменили, а не перечисление файлов.
- Не коммитить секреты: `.env`, токены, пароли (они в `.gitignore`).

Примеры:

```
Fix Docker entrypoint CRLF on Windows

Add scheduled purge for expired seizure retention records
```

## Pull Request

В описании PR указывать:

1. **Summary** — что сделано и зачем (1–3 пункта).
2. **Test plan** — как проверить (`pytest`, `docker compose up`, ручной сценарий в боте).

После merge на GitHub — удалить remote-ветку (кнопка «Delete branch»).

## Чего не делать

- Не копить долгоживущие ветки вроде `test-branch` — только короткие ветки под конкретную задачу.
- Не делать `--force` push в `master`.
- Не коммитить `--amend` / force push, если коммит уже запушен и кто-то мог его забрать.

## Локальная проверка перед PR

```bash
docker compose up -d --build
docker compose logs -f bot

# если есть Poetry локально:
poetry run alembic upgrade head
poetry run pytest -q
```

## Для AI / Cursor

При работе над этим репозиторием:

1. Создавать **feature/fix/refactor-ветку** от актуального `master`, а не коммитить напрямую в `master`.
2. Коммитить только по явной просьбе пользователя.
3. Push и PR — только по явной просьбе; по умолчанию останавливаться после коммита в feature-ветке.
4. Следовать структуре проекта: `handlers` → `use_cases` → `database/repositories`, без лишней связки aiogram в `services/`.
5. **Тексты пользователю** — только через `i18n.t("domain.key")` и YAML в `locales/`. Не хардкодить строки в handlers/keyboards.
6. Новые сообщения добавлять в `locales/ru/*.yaml` (по домену), с `{placeholders}` для подстановок.
