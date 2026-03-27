"""Telegram bot entrypoint: webhook for prod, polling for dev."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.methods import DeleteWebhook, SetWebhook
from aiogram.types import BotCommand, BotCommandScopeChat, MenuButtonCommands
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.admin_error_notify import register_admin_error_alerts
from bot.handlers.flow import build_flow_router
from bot.handlers.menu import build_menu_router
from bot.telegram_safe import install_callback_query_answer_guard
from bot.analytics_middleware import BotInteractionAnalyticsMiddleware
from bot.identity_middleware import TelegramIdentityMiddleware
from bot.locale_middleware import LocaleMiddleware
from infrastructure.config import Settings, load_settings
from infrastructure.incidents import IncidentStore
from infrastructure.logging_setup import setup_logging
from infrastructure.runtime import BotRuntime, build_bot_runtime
from shared.locale import t

log = logging.getLogger(__name__)


async def _shutdown_hooks(rt: BotRuntime) -> None:
    for hook in rt.shutdown_hooks:
        try:
            await hook()
        except Exception:
            log.exception("shutdown hook failed")


async def _configure_commands(bot: Bot, settings: Settings) -> None:
    def _cmds(loc: str) -> list[BotCommand]:
        return [
            BotCommand(command="start", description=t(loc, "cmd_start")),
            BotCommand(command="menu", description=t(loc, "cmd_menu")),
            BotCommand(command="about", description=t(loc, "cmd_about")),
            BotCommand(command="feedback", description=t(loc, "cmd_feedback")),
            BotCommand(command="donate", description=t(loc, "cmd_donate")),
        ]

    default_ru = _cmds("ru")
    default_en = _cmds("en")
    await bot.set_my_commands(default_ru)
    await bot.set_my_commands(default_en, language_code="en")
    for admin_id in sorted(settings.admin_ids):
        admin_ru = [*default_ru, BotCommand(command="admin", description=t("ru", "cmd_admin"))]
        admin_en = [*default_en, BotCommand(command="admin", description=t("en", "cmd_admin"))]
        await bot.set_my_commands(admin_ru, scope=BotCommandScopeChat(chat_id=admin_id))
        await bot.set_my_commands(admin_en, scope=BotCommandScopeChat(chat_id=admin_id), language_code="en")
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

def _build_dispatcher(rt: BotRuntime) -> Dispatcher:
    install_callback_query_answer_guard()
    dp = Dispatcher(
        storage=rt.fsm_storage,
        events_isolation=rt.event_isolation,
    )
    dp.update.middleware(TelegramIdentityMiddleware(rt.ctx))
    dp.update.middleware(LocaleMiddleware())
    dp.update.middleware(BotInteractionAnalyticsMiddleware(rt.ctx))
    dp.include_router(build_menu_router(rt.ctx))
    dp.include_router(build_flow_router(rt.ctx))
    return dp


async def _build_bot(settings: Settings) -> Bot:
    session = AiohttpSession(limit=settings.aiohttp_connection_limit)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await _configure_commands(bot, settings)
    return bot


async def _notify_admins(bot: Bot, settings: Settings, text: str) -> None:
    for admin_id in sorted(settings.admin_ids):
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except Exception:
            log.exception("admin notification failed for %s", admin_id)


async def _notify_admins_bootstrap(settings: Settings, text: str) -> None:
    """Если основной Bot ещё не собран — одноразовая отправка тем же токеном."""
    disposable = Bot(
        token=settings.bot_token,
        session=AiohttpSession(limit=min(32, settings.aiohttp_connection_limit)),
    )
    try:
        await _notify_admins(disposable, settings, text)
    finally:
        try:
            await disposable.session.close()
        except Exception:
            log.exception("bootstrap bot session close failed")


def _problem_text(reason: str, restart_delay: int) -> str:
    return t("ru", "main_incident_problem", reason=reason, restart_delay=restart_delay)


def _resolved_text(reason: str | None) -> str:
    base = t("ru", "main_incident_resolved")
    if reason:
        return base + t("ru", "main_incident_resolved_suffix", reason=reason)
    return base


async def _run_polling(settings: Settings, bot: Bot, stop_event: asyncio.Event) -> None:
    rt = await build_bot_runtime(settings)
    dp = _build_dispatcher(rt)
    register_admin_error_alerts(dp, bot, settings)
    allowed_updates = dp.resolve_used_update_types()

    log.info(
        "HumanOS polling (env=%s, backend=%s)",
        settings.env,
        "redis" if settings.use_redis else "file",
    )
    try:
        await bot(DeleteWebhook(drop_pending_updates=settings.webhook_drop_pending_updates))
        polling_task = asyncio.create_task(
            dp.start_polling(
                bot,
                allowed_updates=allowed_updates,
                handle_signals=False,
            )
        )
        stop_task = asyncio.create_task(stop_event.wait())
        done, pending = await asyncio.wait(
            {polling_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if stop_task in done and not polling_task.done():
            await dp.stop_polling()
        for task in pending:
            task.cancel()
        await polling_task
    finally:
        await _shutdown_hooks(rt)


async def _run_webhook_once(settings: Settings, bot: Bot, stop_event: asyncio.Event) -> None:
    rt = await build_bot_runtime(settings)
    dp = _build_dispatcher(rt)
    register_admin_error_alerts(dp, bot, settings)
    allowed_updates = dp.resolve_used_update_types()

    app = web.Application()
    request_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        handle_in_background=True,
        secret_token=settings.webhook_secret,
    )
    request_handler.register(app, path=settings.webhook_path)
    setup_application(app, dp, bot=bot)

    async def _on_startup(_: web.Application) -> None:
        assert settings.webhook_url is not None
        await bot(
            SetWebhook(
                url=settings.webhook_url,
                secret_token=settings.webhook_secret,
                allowed_updates=allowed_updates,
                drop_pending_updates=settings.webhook_drop_pending_updates,
                max_connections=settings.webhook_max_connections,
            )
        )
        log.info(
            "HumanOS webhook (env=%s, backend=%s, url=%s)",
            settings.env,
            "redis" if settings.use_redis else "file",
            settings.webhook_url,
        )

    async def _on_shutdown(_: web.Application) -> None:
        return None

    app.on_startup.append(_on_startup)
    app.on_shutdown.append(_on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner,
        host=settings.webhook_host,
        port=settings.webhook_port,
        backlog=settings.webhook_listen_backlog,
    )
    try:
        await site.start()
        await stop_event.wait()
    finally:
        await runner.cleanup()
        await _shutdown_hooks(rt)


async def _run_forever(stop_event: asyncio.Event) -> None:
    restart_delay = 3
    while not stop_event.is_set():
        settings = load_settings()
        setup_logging(log_dir=settings.log_dir)
        incidents = IncidentStore(settings.project_root)
        bot: Bot | None = None
        try:
            bot = await _build_bot(settings)
            incident = incidents.resolve_active()
            if incident and settings.admin_ids:
                await _notify_admins(bot, settings, _resolved_text(incident.last_problem_reason))
            restart_delay = 3

            if settings.use_webhook:
                await _run_webhook_once(settings, bot, stop_event)
            else:
                await _run_polling(settings, bot, stop_event)

            if stop_event.is_set():
                break

            reason = "runtime stopped unexpectedly"
            if settings.admin_ids:
                await _notify_admins(bot, settings, _problem_text(reason, restart_delay))
            incidents.mark_problem(reason)
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            log.exception("HumanOS runtime crashed")
            incidents.mark_problem(reason)
            if settings.admin_ids:
                alert = _problem_text(reason, restart_delay)
                if bot is not None:
                    await _notify_admins(bot, settings, alert)
                else:
                    await _notify_admins_bootstrap(settings, alert)
        finally:
            if bot is not None:
                try:
                    await bot.session.close()
                except Exception:
                    log.exception("bot session close failed")
        if stop_event.is_set():
            break
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=restart_delay)
        except asyncio.TimeoutError:
            pass
        restart_delay = min(restart_delay * 2, 60)


def main() -> None:
    async def runner() -> None:
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop_event.set)
            except NotImplementedError:
                continue
        await _run_forever(stop_event)

    asyncio.run(runner())


if __name__ == "__main__":
    main()
