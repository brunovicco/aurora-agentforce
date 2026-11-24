import sqlite3
from contextlib import closing
from datetime import timedelta
from pathlib import Path

from aurora_orders.adapters.sqlite_bindings import SQLiteBindingStore
from tests.conftest import NOW
from tests.test_context_broker import make_client, register, resolve


def test_persistent_binding_survives_restart_and_revocation(tmp_path: Path) -> None:
    path = tmp_path / "bindings.sqlite3"
    first = SQLiteBindingStore(path)
    register(first)
    with make_client(first) as client:
        headers = resolve(client)
    reopened = SQLiteBindingStore(path)
    with make_client(reopened) as client:
        assert client.get("/verified/orders/AUR-1001", headers=headers).status_code == 200
        assert client.get("/verified/orders/AUR-9001", headers=headers).status_code == 404
        reopened.revoke("conversation-1")
    with make_client(SQLiteBindingStore(path)) as client:
        assert client.get("/verified/orders/AUR-1001", headers=headers).status_code == 401
    assert headers["X-Aurora-Customer-Session"].encode() not in path.read_bytes()


def test_replacement_scope_expiry_and_audit(tmp_path: Path) -> None:
    path = tmp_path / "bindings.sqlite3"
    store = SQLiteBindingStore(path)
    register(store)
    previous = store.resolve("conversation-1", "user-1", NOW)
    assert previous is not None
    assert store.resolve("conversation-1", "wrong-user", NOW) is None
    register(store, "customer-demo-002")
    assert not store.is_active(previous.customer, NOW)
    current = store.resolve("conversation-1", "user-1", NOW)
    assert current is not None
    assert current.customer != previous.customer
    assert store.is_active(current.customer, NOW)
    assert not store.is_active(current.customer, NOW + timedelta(minutes=2))
    assert store.resolve("conversation-1", "user-1", NOW + timedelta(minutes=2)) is None
    with closing(sqlite3.connect(path)) as db:
        events = db.execute("SELECT event_type FROM audit_events ORDER BY event_id").fetchall()
    assert [event[0] for event in events] == [
        "binding_registered_or_replaced",
        "context_resolved",
        "context_denied",
        "binding_registered_or_replaced",
        "session_denied",
        "context_resolved",
        "session_active",
        "session_denied",
        "context_denied",
    ]
