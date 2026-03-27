from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from app.use_cases.context import AppContext
from domain.protocols import build_default_protocol_engine
from infrastructure.analytics import Analytics
from infrastructure.auth_tokens import AuthTokenCodec
from infrastructure.client_store import ClientStore
from infrastructure.feedback_store import FeedbackStore
from infrastructure.incidents import IncidentStore
from infrastructure.push import default_push_triggers
from infrastructure.release_store import ReleaseStore
from infrastructure.storage.memory import InMemoryUserRepository


def test_api_start_and_select_state(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    ctx = AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        res = client.post("/v1/start", json={"user_id": "telegram-1", "app_type": "web"})
        assert res.status_code == 200
        assert len(res.json()["states"]) == 6

        res = client.post(
            "/v1/select-state",
            json={"user_id": "telegram-1", "state_key": "tired", "app_type": "web"},
        )
        assert res.status_code == 200
        assert res.json()["state_key"] == "tired"
        assert ctx.analytics.summary(period_key="today").app_type_counts["web"] == 2


def test_api_rating_validation(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    ctx = AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        res = client.post("/v1/protocol/start", json={"user_id": "telegram-1", "rating": 6})
        assert res.status_code == 422


def test_api_auth_session(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    ctx = AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        res = client.post(
            "/v1/auth/session",
            json={"provider": "web", "subject": "u-42", "display_name": "Alice", "scopes": ["profile:read"]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["token_type"] == "bearer"
        assert body["actor_id"] == "web:u-42"
        assert body["client_id"]
        assert body["role"] == "client"


def test_api_donation_redirect_tracks_and_redirects(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    ctx = AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        res = client.get(
            "/r/donate",
            params={"user_id": "telegram-1", "source": "donate_menu", "app_type": "web"},
            follow_redirects=False,
        )
        assert res.status_code == 307
        assert res.headers["location"] == settings.tribute_url
        summary = ctx.analytics.summary(period_key="today")
        assert summary.donation_clicks == 1
        assert summary.app_type_counts["web"] == 1


def test_api_requires_secret_and_bearer_when_enabled(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    secured_settings = replace(settings, api_shared_secret="bootstrap-secret")
    ctx = AppContext(
        settings=secured_settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(secured_settings.project_root),
        feedback_store=FeedbackStore(secured_settings.project_root),
        release_store=ReleaseStore(secured_settings.project_root),
        clients=ClientStore(secured_settings.client_db_path, admin_ids=secured_settings.admin_ids),
        auth_tokens=AuthTokenCodec(secured_settings.auth_token_secret, ttl_seconds=secured_settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: secured_settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        denied = client.post("/v1/start", json={"user_id": "u-42", "app_type": "web"})
        assert denied.status_code == 401

        auth = client.post(
            "/v1/auth/session",
            headers={"X-API-Key": "bootstrap-secret"},
            json={"provider": "web", "subject": "u-42", "display_name": "Alice"},
        )
        assert auth.status_code == 200
        token = auth.json()["access_token"]

        allowed = client.post(
            "/v1/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "u-42", "app_type": "web"},
        )
        assert allowed.status_code == 200

        mismatch = client.post(
            "/v1/select-state",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "someone-else", "state_key": "tired", "app_type": "web"},
        )
        assert mismatch.status_code == 403


def test_api_rate_limit_returns_429(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    tight_settings = replace(settings, api_rate_limit_max_requests=1, api_rate_limit_window_seconds=60)
    ctx = AppContext(
        settings=tight_settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(tight_settings.project_root),
        feedback_store=FeedbackStore(tight_settings.project_root),
        release_store=ReleaseStore(tight_settings.project_root),
        clients=ClientStore(tight_settings.client_db_path, admin_ids=tight_settings.admin_ids),
        auth_tokens=AuthTokenCodec(tight_settings.auth_token_secret, ttl_seconds=tight_settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: tight_settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        first = client.post("/v1/start", json={"user_id": "telegram-1", "app_type": "web"})
        second = client.post("/v1/start", json={"user_id": "telegram-1", "app_type": "web"})
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.headers["retry-after"]


def test_healthz_returns_runtime_snapshot(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    ctx = AppContext(
        settings=settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(settings.project_root),
        feedback_store=FeedbackStore(settings.project_root),
        release_store=ReleaseStore(settings.project_root),
        clients=ClientStore(settings.client_db_path, admin_ids=settings.admin_ids),
        auth_tokens=AuthTokenCodec(settings.auth_token_secret, ttl_seconds=settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        res = client.get("/healthz")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["component"] == "api"
        assert body["storage_backend"] == "file"
        assert body["rate_limit"]["max_requests"] == settings.api_rate_limit_max_requests
        assert body["client_db"]["status"] == "ok"


def test_client_management_api_and_self_access(monkeypatch, settings) -> None:
    from interfaces.api import main as api_main

    secured_settings = replace(settings, api_shared_secret="bootstrap-secret")
    clients = ClientStore(secured_settings.client_db_path, admin_ids=secured_settings.admin_ids)
    ctx = AppContext(
        settings=secured_settings,
        users=InMemoryUserRepository(),
        analytics=Analytics(),
        protocols=build_default_protocol_engine(),
        incidents=IncidentStore(secured_settings.project_root),
        feedback_store=FeedbackStore(secured_settings.project_root),
        release_store=ReleaseStore(secured_settings.project_root),
        clients=clients,
        auth_tokens=AuthTokenCodec(secured_settings.auth_token_secret, ttl_seconds=secured_settings.auth_token_ttl_seconds),
        push_triggers=default_push_triggers(),
    )

    async def fake_build_api_context(_settings):
        return ctx, []

    monkeypatch.setattr(api_main, "load_settings", lambda: secured_settings)
    monkeypatch.setattr(api_main, "build_api_context", fake_build_api_context)

    with TestClient(api_main.app) as client:
        created = client.post(
            "/v1/clients/upsert-identity",
            headers={"X-API-Key": "bootstrap-secret"},
            json={
                "provider": "web",
                "subject": "user-1",
                "display_name": "User One",
                "role": "client",
            },
        )
        assert created.status_code == 200
        client_id = created.json()["client"]["client_id"]

        token_res = client.post(
            "/v1/auth/session",
            headers={"X-API-Key": "bootstrap-secret"},
            json={"provider": "web", "subject": "user-1", "display_name": "User One"},
        )
        assert token_res.status_code == 200
        token = token_res.json()["access_token"]

        own_client = client.get(
            f"/v1/clients/{client_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert own_client.status_code == 200
        assert own_client.json()["client"]["client_id"] == client_id

        denied_role_patch = client.patch(
            f"/v1/clients/{client_id}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "admin"},
        )
        assert denied_role_patch.status_code == 403

        listed = client.get("/v1/clients", headers={"X-API-Key": "bootstrap-secret"})
        assert listed.status_code == 200
        assert listed.json()["items"]
