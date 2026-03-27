"""Load settings from environment. All paths stay inside the project root."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Project root: .../humanos (parent of infrastructure/)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "configs"
LOG_DIR = PROJECT_ROOT / "logs"


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration (no secrets logged)."""

    bot_token: str
    tribute_url: str
    bot_public_url: str
    env: str
    admin_ids: frozenset[int]
    project_root: Path
    log_dir: Path
    redis_url: str | None
    redis_key_prefix: str
    fsm_ttl_seconds: int | None
    session_ttl_seconds: int | None
    webhook_base_url: str | None
    webhook_secret: str | None
    webhook_path: str
    webhook_host: str
    webhook_port: int
    webhook_max_connections: int
    webhook_listen_backlog: int
    webhook_drop_pending_updates: bool
    auth_token_secret: str
    auth_token_ttl_seconds: int
    api_shared_secret: str | None
    api_rate_limit_max_requests: int
    api_rate_limit_window_seconds: int
    analytics_max_file_bytes: int
    analytics_backup_count: int
    analytics_writer_batch_size: int
    analytics_writer_flush_seconds: float
    analytics_writer_queue_max: int
    aiohttp_connection_limit: int
    # Hide bottom reply menu during inline flows; re-open via client keyboard icon or /menu.
    bot_hide_reply_keyboard_outside_home: bool
    # Min seconds between identity DB syncs when Telegram profile fields are unchanged.
    bot_identity_resync_seconds: float

    @property
    def is_prod(self) -> bool:
        return self.env.lower() == "prod"

    def is_admin(self, user_id: int | str) -> bool:
        try:
            return int(user_id) in self.admin_ids
        except (TypeError, ValueError):
            return False

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def use_webhook(self) -> bool:
        return bool(self.webhook_base_url)

    @property
    def webhook_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return f"{self.webhook_base_url.rstrip('/')}/{self.webhook_path.lstrip('/')}"

    @property
    def public_http_base_url(self) -> str | None:
        if not self.webhook_base_url:
            return None
        return self.webhook_base_url.rstrip("/")

    @property
    def api_auth_enabled(self) -> bool:
        return bool(self.api_shared_secret)

    @property
    def transport_mode(self) -> str:
        return "webhook" if self.use_webhook else "polling"

    @property
    def client_db_path(self) -> Path:
        return self.project_root / "data" / "runtime" / "clients.sqlite3"


def _to_bool(value: str, *, default: bool) -> bool:
    raw = value.strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def load_settings(*, env_file: Path | None = None) -> Settings:
    """
    Load ``.env`` from project root (same directory as this package's parent).

    Required: BOT_TOKEN, TRIBUTE_URL, ENV.
    """
    dotenv_path = env_file or (PROJECT_ROOT / ".env")
    # ``override=True``: values from this project's .env win over pre-set os.environ
    # (shell export, systemd Environment=, CI). Otherwise a stale BOT_TOKEN in the
    # environment silently shadows the file — a common cause of "invalid token".
    load_dotenv(dotenv_path, override=True)

    token = os.getenv("BOT_TOKEN", "").strip()
    tribute = os.getenv("TRIBUTE_URL", "").strip()
    bot_public_url = os.getenv("BOT_PUBLIC_URL", "https://t.me/HumanOS_robot").strip() or "https://t.me/HumanOS_robot"
    env = os.getenv("ENV", "dev").strip() or "dev"
    admin_ids = frozenset(
        int(chunk.strip())
        for chunk in os.getenv("ADMIN_IDS", "").split(",")
        if chunk.strip().isdigit()
    )
    redis_url = os.getenv("REDIS_URL", "").strip() or None
    redis_key_prefix = (os.getenv("REDIS_KEY_PREFIX", "humanos").strip() or "humanos").rstrip(":")
    fsm_ttl_raw = os.getenv("FSM_TTL_SECONDS", "604800").strip()
    session_ttl_raw = os.getenv("SESSION_TTL_SECONDS", "1209600").strip()
    fsm_ttl_seconds: int | None = int(fsm_ttl_raw) if fsm_ttl_raw else None
    session_ttl_seconds: int | None = int(session_ttl_raw) if session_ttl_raw else None
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "").strip() or None
    webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip() or None
    webhook_path = os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip() or "/telegram/webhook"
    webhook_host = os.getenv("WEBHOOK_HOST", "0.0.0.0").strip() or "0.0.0.0"
    webhook_port = int((os.getenv("WEBHOOK_PORT", "8080").strip() or "8080"))
    # Telegram API: max 100 simultaneous webhook connections per bot
    webhook_max_connections = min(
        100,
        max(1, int((os.getenv("WEBHOOK_MAX_CONNECTIONS", "100").strip() or "100"))),
    )
    webhook_listen_backlog = min(
        65_535,
        max(128, int((os.getenv("WEBHOOK_LISTEN_BACKLOG", "2048").strip() or "2048"))),
    )
    webhook_drop_pending_updates = _to_bool(
        os.getenv("WEBHOOK_DROP_PENDING_UPDATES", "false"),
        default=False,
    )
    explicit_auth_token_secret = os.getenv("AUTH_TOKEN_SECRET", "").strip()
    auth_token_secret = explicit_auth_token_secret or f"humanos::{token}"
    auth_token_ttl_seconds = int((os.getenv("AUTH_TOKEN_TTL_SECONDS", "2592000").strip() or "2592000"))
    api_shared_secret = os.getenv("API_SHARED_SECRET", "").strip() or None
    api_rate_limit_max_requests = int((os.getenv("API_RATE_LIMIT_MAX_REQUESTS", "120").strip() or "120"))
    api_rate_limit_window_seconds = int((os.getenv("API_RATE_LIMIT_WINDOW_SECONDS", "60").strip() or "60"))
    analytics_max_file_bytes = int((os.getenv("ANALYTICS_MAX_FILE_BYTES", "5242880").strip() or "5242880"))
    analytics_backup_count = int((os.getenv("ANALYTICS_BACKUP_COUNT", "3").strip() or "3"))
    analytics_writer_batch_size = max(1, int((os.getenv("ANALYTICS_WRITER_BATCH_SIZE", "200").strip() or "200")))
    analytics_writer_flush_seconds = max(
        0.05,
        float((os.getenv("ANALYTICS_WRITER_FLUSH_MS", "250").strip() or "250")) / 1000.0,
    )
    analytics_writer_queue_max = max(1000, int((os.getenv("ANALYTICS_WRITER_QUEUE_MAX", "200000").strip() or "200000")))
    aiohttp_connection_limit = max(50, int((os.getenv("TELEGRAM_AIOHTTP_LIMIT", "300").strip() or "300")))
    bot_hide_reply_keyboard_outside_home = _to_bool(
        os.getenv("BOT_HIDE_REPLY_KEYBOARD_OUTSIDE_HOME", "true"),
        default=True,
    )
    _id_resync_raw = (os.getenv("BOT_IDENTITY_RESYNC_SECONDS", "60").strip() or "60")
    bot_identity_resync_seconds = max(5.0, float(_id_resync_raw))

    if not token:
        raise RuntimeError("BOT_TOKEN is required in .env")
    if not tribute:
        raise RuntimeError("TRIBUTE_URL is required in .env")
    if env.lower() == "prod" and webhook_base_url and not webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET is required in prod when WEBHOOK_BASE_URL is set")
    if env.lower() == "prod" and not explicit_auth_token_secret:
        raise RuntimeError("AUTH_TOKEN_SECRET must be set explicitly in prod")
    if env.lower() == "prod" and webhook_base_url and not webhook_base_url.lower().startswith("https://"):
        raise RuntimeError("WEBHOOK_BASE_URL must use https in prod")
    if api_rate_limit_max_requests < 1:
        raise RuntimeError("API_RATE_LIMIT_MAX_REQUESTS must be >= 1")
    if api_rate_limit_window_seconds < 1:
        raise RuntimeError("API_RATE_LIMIT_WINDOW_SECONDS must be >= 1")

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        bot_token=token,
        tribute_url=tribute.rstrip("/"),
        bot_public_url=bot_public_url.rstrip("/"),
        env=env,
        admin_ids=admin_ids,
        project_root=PROJECT_ROOT,
        log_dir=log_dir,
        redis_url=redis_url,
        redis_key_prefix=redis_key_prefix,
        fsm_ttl_seconds=fsm_ttl_seconds,
        session_ttl_seconds=session_ttl_seconds,
        webhook_base_url=webhook_base_url,
        webhook_secret=webhook_secret,
        webhook_path=webhook_path,
        webhook_host=webhook_host,
        webhook_port=webhook_port,
        webhook_max_connections=webhook_max_connections,
        webhook_listen_backlog=webhook_listen_backlog,
        webhook_drop_pending_updates=webhook_drop_pending_updates,
        auth_token_secret=auth_token_secret,
        auth_token_ttl_seconds=auth_token_ttl_seconds,
        api_shared_secret=api_shared_secret,
        api_rate_limit_max_requests=api_rate_limit_max_requests,
        api_rate_limit_window_seconds=api_rate_limit_window_seconds,
        analytics_max_file_bytes=analytics_max_file_bytes,
        analytics_backup_count=analytics_backup_count,
        analytics_writer_batch_size=analytics_writer_batch_size,
        analytics_writer_flush_seconds=analytics_writer_flush_seconds,
        analytics_writer_queue_max=analytics_writer_queue_max,
        aiohttp_connection_limit=aiohttp_connection_limit,
        bot_hide_reply_keyboard_outside_home=bot_hide_reply_keyboard_outside_home,
        bot_identity_resync_seconds=bot_identity_resync_seconds,
    )
