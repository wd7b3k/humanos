# HumanOS

Репозиторий: [github.com/wd7b3k/humanos](https://github.com/wd7b3k/humanos) (ветка `main`). Синхронизация: `./scripts/sync-github.sh`.

Telegram-бот на **aiogram 3.x** с разделением на transport / application / domain / infrastructure. Бизнес-логика не зависит от Telegram; те же use cases можно вызывать из **FastAPI** (заготовка в `interfaces/api/`).

Проект рассчитан на изолированное развёртывание в `/opt/humanos`: без путей к другим проектам, логи и venv — только внутри каталога.

Главный подробный документ проекта в корне: `HANDBOOK.md`. Релизы текстов протоколов и админка: `docs/RELEASES.md`.

## Структура

```
humanos/
  bot/              # Telegram: handlers, FSM, keyboards, тексты «О сервисе»
  app/              # Сценарии (use cases)
  domain/           # ProtocolEngine и модели
  infrastructure/   # config, logging, storage, analytics
  interfaces/       # FastAPI и будущие транспорты (web, MAX)
  shared/           # DTO, константы
  configs/          # пример systemd unit
  logs/             # app.log, error.log (ротация)
  scripts/          # run.sh
```

## Установка

На Debian/Ubuntu при ошибке `ensurepip is not available` установите пакет venv:

`sudo apt install python3-venv` (версия может отличаться, например `python3.12-venv`).

```bash
cd /opt/humanos
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# отредактируйте .env: BOT_TOKEN, TRIBUTE_URL, BOT_PUBLIC_URL, ENV, ADMIN_IDS; для нагрузки — REDIS_URL
```

## Запуск бота (polling)

Из каталога проекта:

```bash
source /opt/humanos/venv/bin/activate
python bot/main.py
```

Или:

```bash
chmod +x scripts/run.sh
./scripts/run.sh
```

Открытые порты для бота **не нужны** (только исходящие к Telegram API).

## Логи

Файлы с ротацией:

- `logs/app.log` — INFO и выше
- `logs/error.log` — ERROR и выше

Если бот падает, `bot/main.py` сам пытается перезапуститься с backoff, а для постоянного процесса рекомендуется `systemd` с `Restart=always`.

Пути задаются от корня проекта в `infrastructure/config.py` и `infrastructure/logging_setup.py`.

## HTTP API (опционально)

Один процесс держит общий `AppContext` (память сессий — в выбранном репозитории).

```bash
cd /opt/humanos
source venv/bin/activate
uvicorn interfaces.api.main:app --app-dir /opt/humanos --host 127.0.0.1 --port 8000
```

Эндпоинты: `/v1/start`, `/v1/select-state`, `/v1/protocol/start`, `/v1/protocol/next`, `/v1/protocol/finish`, `/v1/donation/click`, `/v1/auth/session`, `/v1/clients`, `/v1/clients/by-identity`, `/v1/clients/upsert-identity`, `/v1/clients/{client_id}`, `/v1/clients/{client_id}/identities`, `/v1/clients/{client_id}/role`, `/r/donate`, `/healthz`.

Для продакшена задайте `API_SHARED_SECRET`: он нужен для выпуска клиентских bearer-токенов через `/v1/auth/session` и защищает бизнес-endpoints API.

Схема доступа:

- `POST /v1/auth/session` с заголовком `X-API-Key: <API_SHARED_SECRET>` выпускает bearer-токен.
- Остальные `POST /v1/*` можно вызывать либо с тем же `X-API-Key`, либо с `Authorization: Bearer <token>`.
- `GET/PATCH /v1/clients*` используют серверную БД клиентов с ролями `client`, `admin`, `service`.
- `/r/donate` и `/healthz` остаются публичными.
- Базовый anti-abuse включён через `API_RATE_LIMIT_MAX_REQUESTS` и `API_RATE_LIMIT_WINDOW_SECONDS`.

## Деплой (systemd)

Скопируйте пример юнита (при необходимости поправьте `User`):

```bash
sudo cp configs/humanos-bot.service.example /etc/systemd/system/humanos-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now humanos-bot.service
sudo journalctl -u humanos-bot.service -f
```

## Масштабирование и хранилище

- **Рекомендуется для продакшена и тысяч параллельных диалогов:** переменная `REDIS_URL` в рабочем `.env`. FSM aiogram и сессии пользователей хранятся в Redis; можно запускать **несколько процессов** polling с одним токеном только при корректной балансировке у Telegram — см. [получение обновлений](https://core.telegram.org/bots/api#getting-updates); обычно один воркер на бота или webhooks.
- **Без `REDIS_URL`:** каталог `data/runtime/` — JSON для FSM и сессий (удобно для dev и одного сервера).
- Репозиторий сессий — **асинхронный** (`async def get/save`): `RedisUserRepository`, `FileUserRepository`, `InMemoryUserRepository` (тесты).
- Отдельная серверная БД клиентов хранится в `data/runtime/clients.sqlite3`: там лежат клиенты, identity mapping и роли доступа.
- Аналитика: `Analytics` (память + JSONL на диске) с ротацией файла через `ANALYTICS_MAX_FILE_BYTES` и `ANALYTICS_BACKUP_COUNT`.
- `GET /healthz` возвращает расширенный runtime-снимок: режим запуска, backend хранения, состояние incident store и текущий release.

## Интерфейс бота

- Закреплённое **нижнее меню**: «Начать», «О сервисе», «Поддержать», «Обратная связь».
- Для админа при наличии `ADMIN_IDS` появляется раздел **«Аналитика»** и команда `/admin`.
- Выбор состояния и оценки **1–5** — инлайн-кнопки (дублируется ввод текстом).
- Раздел **«О сервисе»**: что такое HumanOS и как проходить протокол.

## Донаты

Кнопка поддержки ведёт на `TRIBUTE_URL` через внутренний редирект `/r/donate`, чтобы сохранять аналитику переходов без дополнительного шага для пользователя.

## Docker

Отдельный `Dockerfile` не включён намеренно; проект не тянет глобальные зависимости и готов к контейнеризации: `WORKDIR /opt/humanos`, копирование исходников, `venv` или multi-stage install из `requirements.txt`, команда `python bot/main.py`.

## Безопасность

- Секреты только в `.env` (через `python-dotenv`).
- Код хранит рабочие данные внутри `/opt/humanos/data` и использует только локальные медиа из `/opt/humanos/assets`.
- В `prod` для webhook обязателен `https` в `WEBHOOK_BASE_URL`.
- Продуктовая аналитика автоматически исключает активность клиентов с ролями `admin` и `service`.
