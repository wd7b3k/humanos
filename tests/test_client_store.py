from __future__ import annotations

from infrastructure.client_store import ClientStore


def test_client_store_upserts_identity_and_role(tmp_path) -> None:
    store = ClientStore(tmp_path / "runtime" / "clients.sqlite3", admin_ids=frozenset({1}))

    admin = store.get_client_by_identity_sync("telegram", "1")
    assert admin is not None
    assert admin.role == "admin"

    client = store.upsert_identity_sync(
        provider="web",
        subject="user-42",
        display_name="Alice",
    )
    assert client.role == "client"

    promoted = store.set_role_sync(client.client_id, "service")
    assert promoted.role == "service"

    same = store.upsert_identity_sync(provider="web", subject="user-42", username="alice")
    assert same.client_id == client.client_id
    assert same.role == "service"
