"""SQLite-backed client directory with identities and roles."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from uuid import uuid4

from domain.client_models import (
    CLIENT_ROLES,
    INTERNAL_ROLES,
    ROLE_ADMIN,
    ROLE_CLIENT,
    ClientIdentityRecord,
    ClientRecord,
    normalize_role,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class ClientStore:
    def __init__(self, db_path: Path, *, admin_ids: frozenset[int] = frozenset()) -> None:
        self._db_path = db_path
        self._admin_ids = frozenset(int(item) for item in admin_ids)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._ensure_admin_clients()

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    client_id TEXT PRIMARY KEY,
                    role TEXT NOT NULL CHECK(role IN ('client','admin','service')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS client_identities (
                    client_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    username TEXT,
                    display_name TEXT,
                    profile_url TEXT,
                    last_seen_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (provider, subject),
                    FOREIGN KEY (client_id) REFERENCES clients(client_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_client_identities_client
                ON client_identities(client_id);

                CREATE INDEX IF NOT EXISTS idx_clients_role
                ON clients(role);
                """
            )

    def _ensure_admin_clients(self) -> None:
        for admin_id in self._admin_ids:
            self.upsert_identity_sync(
                provider="telegram",
                subject=str(admin_id),
                role=ROLE_ADMIN,
            )

    def _row_to_client(self, row: sqlite3.Row) -> ClientRecord:
        return ClientRecord(
            client_id=str(row["client_id"]),
            role=str(row["role"]),
            is_active=bool(row["is_active"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _row_to_identity(self, row: sqlite3.Row) -> ClientIdentityRecord:
        return ClientIdentityRecord(
            client_id=str(row["client_id"]),
            provider=str(row["provider"]),
            subject=str(row["subject"]),
            username=row["username"],
            display_name=row["display_name"],
            profile_url=row["profile_url"],
            last_seen_at=row["last_seen_at"],
        )

    def upsert_identity_sync(
        self,
        *,
        provider: str,
        subject: str,
        username: str | None = None,
        display_name: str | None = None,
        profile_url: str | None = None,
        last_seen_at: str | None = None,
        role: str | None = None,
    ) -> ClientRecord:
        normalized_provider = (provider or "").strip().lower()
        normalized_subject = (subject or "").strip()
        if not normalized_provider or not normalized_subject:
            raise ValueError("provider and subject are required")
        normalized_role = normalize_role(role) if role is not None else None
        now = _now_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.client_id, c.role, c.is_active, c.created_at, c.updated_at
                FROM client_identities ci
                JOIN clients c ON c.client_id = ci.client_id
                WHERE ci.provider = ? AND ci.subject = ?
                """,
                (normalized_provider, normalized_subject),
            ).fetchone()
            if row is None:
                client_id = str(uuid4())
                conn.execute(
                    """
                    INSERT INTO clients(client_id, role, is_active, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (client_id, normalized_role or ROLE_CLIENT, now, now),
                )
                conn.execute(
                    """
                    INSERT INTO client_identities(
                        client_id, provider, subject, username, display_name, profile_url,
                        last_seen_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        client_id,
                        normalized_provider,
                        normalized_subject,
                        username,
                        display_name,
                        profile_url,
                        last_seen_at,
                        now,
                        now,
                    ),
                )
                created = conn.execute(
                    "SELECT client_id, role, is_active, created_at, updated_at FROM clients WHERE client_id = ?",
                    (client_id,),
                ).fetchone()
                assert created is not None
                return self._row_to_client(created)

            client = self._row_to_client(row)
            next_role = normalized_role or client.role
            if next_role != client.role:
                conn.execute(
                    "UPDATE clients SET role = ?, updated_at = ? WHERE client_id = ?",
                    (next_role, now, client.client_id),
                )
            conn.execute(
                """
                UPDATE client_identities
                SET username = ?, display_name = ?, profile_url = ?, last_seen_at = ?, updated_at = ?
                WHERE provider = ? AND subject = ?
                """,
                (
                    username,
                    display_name,
                    profile_url,
                    last_seen_at,
                    now,
                    normalized_provider,
                    normalized_subject,
                ),
            )
            updated = conn.execute(
                "SELECT client_id, role, is_active, created_at, updated_at FROM clients WHERE client_id = ?",
                (client.client_id,),
            ).fetchone()
            assert updated is not None
            return self._row_to_client(updated)

    async def upsert_identity(self, **kwargs) -> ClientRecord:
        return await asyncio.to_thread(self.upsert_identity_sync, **kwargs)

    def get_client_sync(self, client_id: str) -> ClientRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT client_id, role, is_active, created_at, updated_at FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        return self._row_to_client(row) if row is not None else None

    async def get_client(self, client_id: str) -> ClientRecord | None:
        return await asyncio.to_thread(self.get_client_sync, client_id)

    def get_client_by_identity_sync(self, provider: str, subject: str) -> ClientRecord | None:
        normalized_provider = (provider or "").strip().lower()
        normalized_subject = (subject or "").strip()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT c.client_id, c.role, c.is_active, c.created_at, c.updated_at
                FROM client_identities ci
                JOIN clients c ON c.client_id = ci.client_id
                WHERE ci.provider = ? AND ci.subject = ?
                """,
                (normalized_provider, normalized_subject),
            ).fetchone()
        return self._row_to_client(row) if row is not None else None

    async def get_client_by_identity(self, provider: str, subject: str) -> ClientRecord | None:
        return await asyncio.to_thread(self.get_client_by_identity_sync, provider, subject)

    def list_clients_sync(self, *, role: str | None = None, limit: int = 100) -> list[ClientRecord]:
        query = "SELECT client_id, role, is_active, created_at, updated_at FROM clients"
        params: tuple[object, ...] = ()
        if role:
            query += " WHERE role = ?"
            params = (normalize_role(role),)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params = (*params, max(1, min(int(limit), 500)))
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_client(row) for row in rows]

    async def list_clients(self, *, role: str | None = None, limit: int = 100) -> list[ClientRecord]:
        return await asyncio.to_thread(self.list_clients_sync, role=role, limit=limit)

    def list_identities_sync(self, client_id: str) -> list[ClientIdentityRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT client_id, provider, subject, username, display_name, profile_url, last_seen_at
                FROM client_identities
                WHERE client_id = ?
                ORDER BY provider, subject
                """,
                (client_id,),
            ).fetchall()
        return [self._row_to_identity(row) for row in rows]

    async def list_identities(self, client_id: str) -> list[ClientIdentityRecord]:
        return await asyncio.to_thread(self.list_identities_sync, client_id)

    def set_role_sync(self, client_id: str, role: str) -> ClientRecord:
        normalized_role = normalize_role(role)
        now = _now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE clients SET role = ?, updated_at = ? WHERE client_id = ?",
                (normalized_role, now, client_id),
            )
            row = conn.execute(
                "SELECT client_id, role, is_active, created_at, updated_at FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        if row is None:
            raise KeyError(client_id)
        return self._row_to_client(row)

    async def set_role(self, client_id: str, role: str) -> ClientRecord:
        return await asyncio.to_thread(self.set_role_sync, client_id, role)

    def resolve_role_sync(self, provider: str, subject: str) -> str | None:
        client = self.get_client_by_identity_sync(provider, subject)
        if client is None or not client.is_active:
            return None
        return client.role

    def is_internal_identity_sync(self, provider: str, subject: str) -> bool:
        role = self.resolve_role_sync(provider, subject)
        return role in INTERNAL_ROLES

    def health_snapshot_sync(self) -> dict[str, object]:
        with self._connect() as conn:
            total_clients = int(conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0])
        return {
            "path": str(self._db_path),
            "total_clients": total_clients,
            "roles": list(CLIENT_ROLES),
            "status": "ok",
        }
