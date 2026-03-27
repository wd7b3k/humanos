"""
HTTP API exposing use cases (Telegram-independent).

Run (dev): ``uvicorn interfaces.api.main:app --app-dir /opt/humanos --reload``
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import hashlib
import logging
import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.use_cases.context import AppContext
from app.use_cases.donation import DonationUseCase
from app.use_cases.finish_protocol import FinishProtocolUseCase
from app.use_cases.next_step import NextStepUseCase
from domain.auth import AuthIdentity
from domain.client_models import INTERNAL_ROLES, ROLE_ADMIN, ROLE_CLIENT, ROLE_SERVICE, ClientIdentityRecord, ClientRecord, normalize_role
from app.use_cases.select_state import SelectStateUseCase
from app.use_cases.start import StartUseCase
from app.use_cases.start_protocol import StartProtocolUseCase
from infrastructure.api_rate_limit import ApiRateLimiter
from infrastructure.config import load_settings
from infrastructure.health import build_runtime_health
from infrastructure.runtime import build_api_context
from shared.constants import RATING_MAX, RATING_MIN
from shared.dto import DonationTrackResult, ErrorResult, FinishResult, ProtocolStartResult, StateSelectedResult

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    if settings.is_prod and not settings.api_shared_secret:
        raise RuntimeError("API_SHARED_SECRET must be set explicitly in prod before starting the HTTP API")
    ctx, hooks = await build_api_context(settings)
    app.state.humanos_ctx = ctx
    app.state.api_rate_limiter = ApiRateLimiter(
        max_requests=settings.api_rate_limit_max_requests,
        window_seconds=settings.api_rate_limit_window_seconds,
    )
    yield
    for h in hooks:
        try:
            await h()
        except Exception:
            log.exception("api shutdown hook failed")


app = FastAPI(title="HumanOS API", version="0.2.0", lifespan=lifespan)


def get_ctx(request: Request) -> AppContext:
    return request.app.state.humanos_ctx


def _read_api_key(request: Request) -> str | None:
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")


def _request_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _client_rate_key(request: Request) -> str:
    api_key = (_read_api_key(request) or "").strip()
    if api_key:
        return f"api-key:{_request_fingerprint(api_key)}"
    authorization = (request.headers.get("Authorization") or "").strip()
    if authorization:
        return f"auth:{_request_fingerprint(authorization)}"
    forwarded_for = (request.headers.get("X-Forwarded-For") or "").split(",", 1)[0].strip()
    if forwarded_for:
        return f"ip:{forwarded_for}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def _enforce_rate_limit(request: Request) -> None:
    limiter: ApiRateLimiter = request.app.state.api_rate_limiter
    decision = limiter.check(f"{request.url.path}:{_client_rate_key(request)}")
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"rate limit exceeded, retry in {decision.retry_after_seconds}s",
        headers={"Retry-After": str(decision.retry_after_seconds)},
    )


def _verify_bootstrap_secret(request: Request) -> None:
    ctx = get_ctx(request)
    shared_secret = ctx.settings.api_shared_secret
    if not shared_secret:
        return
    provided = (_read_api_key(request) or "").strip()
    if not provided or not secrets.compare_digest(provided, shared_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )


def _require_bearer_session(request: Request):
    ctx = get_ctx(request)
    authorization = (request.headers.get("Authorization") or "").strip()
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )
    token = authorization[7:].strip()
    try:
        return ctx.auth_tokens.verify_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def _has_bootstrap_access(request: Request) -> bool:
    ctx = get_ctx(request)
    shared_secret = ctx.settings.api_shared_secret
    if not shared_secret:
        return True
    provided = (_read_api_key(request) or "").strip()
    return bool(provided) and secrets.compare_digest(provided, shared_secret)


def _require_management_access(request: Request):
    if _has_bootstrap_access(request):
        return None
    session = _require_bearer_session(request)
    if (session.role or "") not in INTERNAL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="management access required",
        )
    return session


def _require_client_or_management_access(request: Request, client_id: str):
    if _has_bootstrap_access(request):
        return None
    session = _require_bearer_session(request)
    if (session.role or "") in INTERNAL_ROLES:
        return session
    if session.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="client access denied",
        )
    return session


def _resolve_authorized_user_id(request: Request, requested_user_id: str) -> str:
    ctx = get_ctx(request)
    shared_secret = ctx.settings.api_shared_secret
    if not shared_secret:
        return requested_user_id

    provided_key = (_read_api_key(request) or "").strip()
    if provided_key and secrets.compare_digest(provided_key, shared_secret):
        return requested_user_id

    session = _require_bearer_session(request)
    allowed_user_ids = {
        session.identity.subject,
        session.identity.actor_id,
    }
    if requested_user_id not in allowed_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_id does not match bearer token",
        )
    return session.identity.actor_id


class UserIdBody(BaseModel):
    user_id: str = Field(..., description="Stable id from your client (e.g. telegram id).")
    app_type: str = Field(default="api", min_length=1, max_length=32)


class StateBody(UserIdBody):
    state_key: str


class RatingBody(UserIdBody):
    rating: int = Field(..., ge=RATING_MIN, le=RATING_MAX)


class DonateBody(UserIdBody):
    source: str = Field(default="api", min_length=1, max_length=64)


class AuthSessionBody(BaseModel):
    provider: str = Field(..., description="Client provider, e.g. web/mobile/max/telegram")
    subject: str = Field(..., description="Stable user id within that provider")
    display_name: str | None = None
    username: str | None = None
    scopes: list[str] = Field(default_factory=list)


class ClientIdentityUpsertBody(BaseModel):
    provider: str = Field(..., min_length=1, max_length=32)
    subject: str = Field(..., min_length=1, max_length=128)
    username: str | None = None
    display_name: str | None = None
    profile_url: str | None = None
    last_seen_at: str | None = None
    role: str | None = Field(default=None, pattern="^(client|admin|service)$")


class ClientRoleBody(BaseModel):
    role: str = Field(..., pattern="^(client|admin|service)$")


def _serialize_client(client: ClientRecord) -> dict[str, Any]:
    return {
        "client_id": client.client_id,
        "role": client.role,
        "is_active": client.is_active,
        "created_at": client.created_at,
        "updated_at": client.updated_at,
    }


def _serialize_identity(identity: ClientIdentityRecord) -> dict[str, Any]:
    return {
        "client_id": identity.client_id,
        "provider": identity.provider,
        "subject": identity.subject,
        "username": identity.username,
        "display_name": identity.display_name,
        "profile_url": identity.profile_url,
        "last_seen_at": identity.last_seen_at,
    }


@app.post("/v1/start")
async def api_start(body: UserIdBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = StartUseCase(get_ctx(request))
    out = await uc.execute(user_id, app_type=body.app_type)
    return {
        "text": out.text,
        "states": [{"key": k, "label": l} for k, l in out.state_labels],
    }


@app.post("/v1/select-state")
async def api_select_state(body: StateBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = SelectStateUseCase(get_ctx(request))
    out = await uc.execute(user_id, body.state_key, app_type=body.app_type)
    if isinstance(out, ErrorResult):
        raise HTTPException(status_code=400, detail=out.message)
    assert isinstance(out, StateSelectedResult)
    return {"text": out.text, "state_key": out.state_key}


@app.post("/v1/protocol/start")
async def api_protocol_start(body: RatingBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = StartProtocolUseCase(get_ctx(request))
    out = await uc.execute(user_id, body.rating, app_type=body.app_type)
    if isinstance(out, ErrorResult):
        raise HTTPException(status_code=400, detail=out.message)
    assert isinstance(out, ProtocolStartResult)
    fs = out.first_step
    return {
        "text": fs.text,
        "step_index": fs.step_index,
        "total_steps": fs.total_steps,
        "is_last_step": fs.is_last_step,
    }


@app.post("/v1/protocol/next")
async def api_protocol_next(body: UserIdBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = NextStepUseCase(get_ctx(request))
    out = await uc.execute(user_id)
    if isinstance(out, ErrorResult):
        raise HTTPException(status_code=400, detail=out.message)
    if out.kind == "need_final_rating":
        return {"status": "need_final_rating"}
    if out.step:
        s = out.step
        return {
            "status": "step",
            "text": s.text,
            "step_index": s.step_index,
            "total_steps": s.total_steps,
            "is_last_step": s.is_last_step,
        }
    raise HTTPException(status_code=500, detail="Invalid next-step payload")


@app.post("/v1/protocol/finish")
async def api_protocol_finish(body: RatingBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = FinishProtocolUseCase(get_ctx(request))
    out = await uc.execute(user_id, body.rating, app_type=body.app_type)
    if isinstance(out, ErrorResult):
        raise HTTPException(status_code=400, detail=out.message)
    assert isinstance(out, FinishResult)
    return {
        "text": out.text,
        "initial_rating": out.initial_rating,
        "final_rating": out.final_rating,
        "improved": out.improved,
        "tribute_url": out.tribute_url,
    }


@app.post("/v1/donation/click")
async def api_donation_click(body: DonateBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    user_id = _resolve_authorized_user_id(request, body.user_id)
    uc = DonationUseCase(get_ctx(request))
    out = await uc.execute(user_id, body.source, app_type=body.app_type)
    assert isinstance(out, DonationTrackResult)
    return {"url": out.url, "source": out.source}


@app.get("/r/donate")
async def redirect_donation_click(
    request: Request,
    user_id: str,
    source: str = "unknown",
    app_type: str = "unknown",
) -> RedirectResponse:
    _enforce_rate_limit(request)
    uc = DonationUseCase(get_ctx(request))
    out = await uc.execute(user_id, source, app_type=app_type)
    assert isinstance(out, DonationTrackResult)
    return RedirectResponse(url=out.url, status_code=307)


@app.post("/v1/auth/session")
async def api_auth_session(body: AuthSessionBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _verify_bootstrap_secret(request)
    ctx = get_ctx(request)
    identity = AuthIdentity(
        provider=body.provider.strip().lower(),
        subject=body.subject.strip(),
        display_name=body.display_name,
        username=body.username,
    )
    client = await ctx.clients.upsert_identity(
        provider=identity.provider,
        subject=identity.subject,
        username=identity.username,
        display_name=identity.display_name,
        role=ROLE_ADMIN if identity.provider == "telegram" and ctx.settings.is_admin(identity.subject) else None,
    )
    requested_scopes = tuple(sorted({scope.strip() for scope in body.scopes if scope.strip()}))
    if client.role == ROLE_CLIENT:
        scopes = ("self",)
    elif client.role in {ROLE_ADMIN, ROLE_SERVICE}:
        scopes = requested_scopes or ("manage",)
    else:
        scopes = requested_scopes
    issued = ctx.auth_tokens.issue_token(
        identity,
        client_id=client.client_id,
        role=client.role,
        scopes=scopes,
    )
    return {
        "access_token": issued.access_token,
        "token_type": "bearer",
        "client_id": client.client_id,
        "role": client.role,
        "actor_id": issued.session.identity.actor_id,
        "provider": issued.session.identity.provider,
        "subject": issued.session.identity.subject,
        "scopes": list(issued.session.scopes),
        "issued_at": issued.session.issued_at,
        "expires_at": issued.session.expires_at,
    }


@app.get("/v1/clients")
async def api_list_clients(request: Request, role: str | None = None, limit: int = 100) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_management_access(request)
    normalized_role = normalize_role(role) if role is not None else None
    clients = await get_ctx(request).clients.list_clients(role=normalized_role, limit=limit)
    return {"items": [_serialize_client(item) for item in clients]}


@app.get("/v1/clients/by-identity")
async def api_client_by_identity(request: Request, provider: str, subject: str) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_management_access(request)
    client = await get_ctx(request).clients.get_client_by_identity(provider, subject)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    identities = await get_ctx(request).clients.list_identities(client.client_id)
    return {
        "client": _serialize_client(client),
        "identities": [_serialize_identity(item) for item in identities],
    }


@app.post("/v1/clients/upsert-identity")
async def api_upsert_client_identity(body: ClientIdentityUpsertBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_management_access(request)
    client = await get_ctx(request).clients.upsert_identity(
        provider=body.provider,
        subject=body.subject,
        username=body.username,
        display_name=body.display_name,
        profile_url=body.profile_url,
        last_seen_at=body.last_seen_at,
        role=body.role,
    )
    return {"client": _serialize_client(client)}


@app.get("/v1/clients/{client_id}")
async def api_get_client(client_id: str, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_client_or_management_access(request, client_id)
    client = await get_ctx(request).clients.get_client(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    return {"client": _serialize_client(client)}


@app.get("/v1/clients/{client_id}/identities")
async def api_get_client_identities(client_id: str, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_client_or_management_access(request, client_id)
    client = await get_ctx(request).clients.get_client(client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="client not found")
    identities = await get_ctx(request).clients.list_identities(client_id)
    return {
        "client": _serialize_client(client),
        "identities": [_serialize_identity(item) for item in identities],
    }


@app.patch("/v1/clients/{client_id}/role")
async def api_patch_client_role(client_id: str, body: ClientRoleBody, request: Request) -> dict[str, Any]:
    _enforce_rate_limit(request)
    _require_management_access(request)
    try:
        client = await get_ctx(request).clients.set_role(client_id, body.role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="client not found") from exc
    return {"client": _serialize_client(client)}


@app.get("/healthz")
def healthz(request: Request) -> dict[str, Any]:
    ctx = get_ctx(request)
    snapshot = build_runtime_health(ctx, component="api").to_dict()
    snapshot["rate_limit"] = {
        "max_requests": ctx.settings.api_rate_limit_max_requests,
        "window_seconds": ctx.settings.api_rate_limit_window_seconds,
    }
    return snapshot
