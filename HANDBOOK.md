# HumanOS Handbook

Единый корневой handbook проекта. Этот файл предназначен одновременно:

- для владельца проекта как актуальная обзорная документация
- для ИИ-агентов как источник истины по архитектуре, runtime и правилам сопровождения

Если меняется поведение системы, API, структура данных, модель прав, деплой или эксплуатация, handbook нужно обновлять в той же задаче.

## 1. Назначение проекта

`HumanOS` - это Telegram-first сервис коротких восстановительных практик с архитектурой, готовой к использованию из других клиентов: web, mobile, API.

Система уже включает:

- Telegram-бот на `aiogram 3.x`
- transport-independent use cases
- file/Redis session storage
- релизы текстов протоколов с архивом и откатом
- persistent analytics
- серверную клиентскую БД с ролями
- HTTP API для внешних клиентов

## 2. Корневые правила документации

Этот handbook - главный документ проекта в корне.

Правила:

1. Не создавать новую "главную" документацию в других местах, если информация должна быть общей для всего проекта.
2. `README.md` остаётся коротким входным документом: запуск, основные команды, быстрый обзор.
3. `HANDBOOK.md` хранит актуальное состояние системы, архитектуру, API, runtime и правила сопровождения.
4. При существенных изменениях нужно синхронно обновлять handbook.
5. Если изменился только узкий технический участок, можно добавить локальную документацию в `docs/`, но handbook всё равно должен получить краткое обновление.

Связанные внутренние документы:

- `docs/PROTOCOL_EVIDENCE.md` — аргументация по техникам и языку
- `docs/RELEASES.md` — релизы текстов протоколов и админка

## 3. Структура проекта

Основные директории:

- `bot/` - Telegram transport: handlers, keyboards, FSM, media, тексты UI
- `app/` - use cases и orchestration без привязки к Telegram
- `domain/` - доменные модели, протоколы, auth и client role model
- `infrastructure/` - config, storage, analytics, runtime, SQLite client DB, file IO
- `interfaces/` - HTTP API
- `shared/` - DTO и константы
- `tests/` - unit/integration tests
- `configs/` - systemd example
- `assets/` - локальные медиа, используемые ботом
- `data/` - runtime data, analytics, release registry, client DB, incident state

## 4. Архитектура

Слои:

- `transport layer`: Telegram handlers и HTTP API endpoints
- `application layer`: use cases в `app/use_cases/`
- `domain layer`: protocol engine, auth/session/client models
- `infrastructure layer`: runtime wiring, config, persistence, analytics, release store

Принцип:

- бизнес-логика не должна зависеть от Telegram
- transport вызывает use cases через `AppContext`
- runtime выбирает backend хранения и собирает зависимости

## 5. Runtime и хранение данных

### 5.1 Пользовательские сессии

Сценарные сессии пользователей хранятся отдельно от клиентской БД:

- `FileUserRepository` для file mode
- `RedisUserRepository` для high-load mode
- `InMemoryUserRepository` для тестов

В сессии лежат:

- выбранное состояние
- рейтинги до/после
- прогресс протокола
- Telegram identity hints
- `client_id` как связка с серверной клиентской БД

### 5.2 Клиентская БД

Серверная БД клиентов живёт в:

- `data/runtime/clients.sqlite3`

Она хранит:

- клиентов
- роли `client`, `admin`, `service`
- identity mapping по `provider + subject`

Роль `admin` синхронизируется из `ADMIN_IDS` и из записей в client DB.

### 5.3 Аналитика

Аналитика хранится в:

- `data/runtime/analytics_events.jsonl`

Свойства:

- буфер в памяти
- фоновая запись на диск
- ротация файла
- загрузка недавнего хвоста при старте
- исключение внутренней активности из продуктовой аналитики

Из аналитики исключаются:

- `admin`
- `service`

Исключение работает:

- на записи новых событий
- на чтении агрегатов и recent events

**Воронка практики (имена событий):** `start`, `state_selected`, `protocol_started`, `protocol_completed`, `improved`, плюс для диагностики UX шагов: `protocol_step_shown` (показ шага; payload: `protocol_id`, `step_index`, `total_steps`), `protocol_next_clicked` (нажатие «Далее»; `from_step_index`), `protocol_abandon_menu` (подтверждённый выход из практики). Трассировка апдейтов: `bot_interaction` (не в суммарных счётчиках воронки).

Журнал **релизов продукта** (код/UX, не JSON протоколов): `docs/PRODUCT_CHANGELOG.md`, скрипт `scripts/record_product_release.sh`.

### 5.4 Релизы текстов

Реестр релизов протоколов:

- `data/protocol_releases/registry.json`
- `data/protocol_releases/releases/*.json`
- `data/runtime/release_events.jsonl`

Это нужно для:

- хранения структуры карточек техник
- версионирования текстов
- rollback
- A/B-готовности

Подробный операционный раздел (файлы, как добавить снимок, админка в Telegram, журнал): **`docs/RELEASES.md`**.

Внутренняя база аргументации по техникам и языку релизов хранится отдельно:

- `docs/PROTOCOL_EVIDENCE.md`

## 6. Identity и права

### 6.1 Identity

Основные идентичности:

- `telegram:<id>`
- будущие `web:<subject>`, `mobile:<subject>`, `service:<subject>`

Telegram identity sync:

- `bot/identity_middleware.py`
- `app/use_cases/identity.py`

Не на каждый апдейт подряд: middleware кэширует «отпечаток» профиля и снова ходит в Redis/SQLite не чаще чем раз в `BOT_IDENTITY_RESYNC_SECONDS` (по умолчанию **180** с; минимум 5). Параллельные апдейты одного пользователя сериализуются `asyncio.Lock`.

Когда срабатывает sync:

- обновляется session state
- делается upsert клиента и identity в SQLite

### 6.2 Роли

Поддерживаемые роли:

- `client` - обычный пользователь
- `admin` - внутренняя роль управления
- `service` - серверный или интеграционный клиент

### 6.3 Правила доступа API

`POST /v1/auth/session`:

- защищён `X-API-Key: API_SHARED_SECRET`
- выпускает bearer token
- токен содержит `client_id` и `role`

User-facing `POST /v1/*`:

- допускают `X-API-Key`
- или `Authorization: Bearer <token>`

Client management endpoints:

- `client` может читать только себя
- `admin` и `service` могут читать и изменять клиентов

## 7. HTTP API

Основные endpoints:

- `POST /v1/start`
- `POST /v1/select-state`
- `POST /v1/protocol/start`
- `POST /v1/protocol/next`
- `POST /v1/protocol/finish`
- `POST /v1/donation/click`
- `POST /v1/auth/session`
- `GET /v1/clients`
- `GET /v1/clients/by-identity`
- `POST /v1/clients/upsert-identity`
- `GET /v1/clients/{client_id}`
- `GET /v1/clients/{client_id}/identities`
- `PATCH /v1/clients/{client_id}/role`
- `GET /r/donate`
- `GET /healthz`

`/healthz` должен считаться главным operational snapshot для API.

## 8. Telegram-часть

Telegram transport отвечает только за:

- приём апдейтов
- FSM
- рендер сообщений и кнопок
- media delivery
- admin menu

Ключевые runtime свойства:

- polling или webhook выбираются через config
- есть auto-restart loop
- admin notifications уходят только админам
- reply keyboard и inline flow разделены

## 9. Эксплуатация

### 9.1 Запуск

Бот:

```bash
source /opt/humanos/venv/bin/activate
python /opt/humanos/bot/main.py
```

API:

```bash
source /opt/humanos/venv/bin/activate
uvicorn interfaces.api.main:app --app-dir /opt/humanos --host 127.0.0.1 --port 8000
```

### 9.2 Сервис

Основной systemd unit:

- `configs/humanos-bot.service.example`

### 9.3 Проверка после изменений

Минимум после существенных правок:

```bash
PYTHONPATH=/opt/humanos /opt/humanos/venv/bin/pytest -q
systemctl restart humanos-bot.service
systemctl is-active humanos-bot.service
```

## 10. Конфигурация

Ключевые переменные:

- `BOT_TOKEN`
- `TRIBUTE_URL`
- `BOT_PUBLIC_URL`
- `ENV`
- `ADMIN_IDS`
- `REDIS_URL`
- `WEBHOOK_BASE_URL`
- `WEBHOOK_SECRET`
- `AUTH_TOKEN_SECRET`
- `API_SHARED_SECRET`
- `API_RATE_LIMIT_MAX_REQUESTS`
- `API_RATE_LIMIT_WINDOW_SECONDS`
- `ANALYTICS_MAX_FILE_BYTES`
- `ANALYTICS_BACKUP_COUNT`

Prod-инварианты:

- `AUTH_TOKEN_SECRET` должен быть явно задан
- для webhook в prod нужен `https`
- HTTP API в prod должен подниматься с `API_SHARED_SECRET`

## 11. Текущее состояние проекта

На текущий момент в проекте уже реализованы и используются:

- Telegram bot runtime с polling/webhook-ready конфигурацией
- file/Redis storage для пользовательских сценарных сессий
- SQLite client DB с ролями `client`, `admin`, `service`
- role-aware HTTP API с bootstrap secret и bearer tokens
- release registry для текстов протоколов с archive/rollback
- persistent analytics с file rotation
- исключение внутренней активности `admin` и `service` из продуктовой аналитики
- расширенный `healthz` для operational snapshot API
- systemd-friendly restart path для живого сервиса

Считать актуальным baseline:

- тесты должны проходить локально через `pytest`
- bot service должен подниматься через `humanos-bot.service`
- handbook должен соответствовать текущему runtime и API

## 12. Известные риски и ограничения

Текущие технические ограничения, которые нужно помнить при будущих изменениях:

- `ClientStore` сейчас построен на `SQLite`, поэтому для многопроцессной high-write нагрузки это промежуточное решение, а не финальный distributed backend
- API rate limiting сейчас in-memory; при запуске нескольких API-процессов лимиты не будут глобально согласованы
- session storage и client DB разделены специально; при будущих миграциях нельзя смешивать сценарное состояние и авторизационные данные в одну таблицу без отдельного решения
- analytics persistence файловая; она уже безопаснее и с ротацией, но для очень большого потока событий позже понадобится внешний ingestion backend
- роль `admin` сейчас синхронизируется и из `ADMIN_IDS`, и из client DB; при развитии панели управления нужно сохранить единый понятный source of truth
- release registry и runtime data хранятся локально в `data/`; при переходе на несколько инстансов потребуется стратегия общего storage

## 13. Ближайшие приоритеты

Если нет более срочной пользовательской задачи, следующий полезный backlog выглядит так:

1. Перевести service access с общего `API_SHARED_SECRET` на отдельные server-to-server credentials, привязанные к записям клиентов
2. Вынести API rate limit в Redis, если API будет запускаться в нескольких процессах или контейнерах
3. Добавить управляемые admin/service workflows поверх client DB, чтобы роли можно было сопровождать без ручной правки окружения
4. Подготовить migration path с `SQLite` на `PostgreSQL`, если клиентская БД станет критичной частью production runtime
5. Добавить более явный operational раздел по backup/restore для `data/runtime/`, `clients.sqlite3` и release registry

## 14. Что ИИ-агент должен поддерживать актуальным

При изменениях нужно обновлять handbook, если затронуто хотя бы одно из:

- новые endpoints или изменение контрактов API
- новые runtime backends, БД, файлы, пути хранения
- новая роль, модель прав или auth flow
- изменение аналитики, release registry или operational behavior
- существенная перестройка Telegram flow
- новые обязательные env vars
- новые команды запуска, проверки, деплоя

Если изменения локальные и handbook не меняется, агент должен явно проверить, что handbook всё ещё актуален.
