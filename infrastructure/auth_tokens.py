"""Signed access tokens for future non-Telegram clients."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from domain.auth import AuthIdentity, AuthSession


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


@dataclass(frozen=True, slots=True)
class IssuedAuthToken:
    access_token: str
    session: AuthSession


class AuthTokenCodec:
    """Stateless HMAC-signed token codec."""

    def __init__(self, secret: str, *, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl_seconds = ttl_seconds

    def issue_token(
        self,
        identity: AuthIdentity,
        *,
        client_id: str | None = None,
        role: str | None = None,
        scopes: tuple[str, ...] = (),
    ) -> IssuedAuthToken:
        now = int(time.time())
        session = AuthSession(
            session_id=secrets.token_urlsafe(18),
            identity=identity,
            client_id=client_id,
            role=role,
            scopes=scopes,
            issued_at=now,
            expires_at=now + self._ttl_seconds,
        )
        payload = {
            "sid": session.session_id,
            "provider": identity.provider,
            "sub": identity.subject,
            "display_name": identity.display_name,
            "username": identity.username,
            "client_id": client_id,
            "role": role,
            "scopes": list(scopes),
            "iat": session.issued_at,
            "exp": session.expires_at,
        }
        encoded = _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        signature = _b64url_encode(hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return IssuedAuthToken(access_token=f"{encoded}.{signature}", session=session)

    def verify_token(self, token: str) -> AuthSession:
        try:
            encoded, signature = token.split(".", 1)
        except ValueError as exc:
            raise ValueError("invalid token format") from exc

        expected = _b64url_encode(hmac.new(self._secret, encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid token signature")

        payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
        now = int(time.time())
        exp = int(payload["exp"])
        if exp < now:
            raise ValueError("token expired")

        identity = AuthIdentity(
            provider=str(payload["provider"]),
            subject=str(payload["sub"]),
            display_name=payload.get("display_name"),
            username=payload.get("username"),
        )
        return AuthSession(
            session_id=str(payload["sid"]),
            identity=identity,
            client_id=payload.get("client_id"),
            role=payload.get("role"),
            scopes=tuple(payload.get("scopes") or ()),
            issued_at=int(payload["iat"]),
            expires_at=exp,
        )
