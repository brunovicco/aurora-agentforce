"""SQLite binding store for an isolated, trusted local deployment."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from aurora_orders.application.context_broker import (
    BindingStoreUnavailable,
    BrokerBinding,
    new_binding,
)
from aurora_orders.application.customer_sessions import VerifiedCustomer


class SQLiteBindingStore:
    """Persist bindings and minimal lifecycle audit events, never bearer tokens."""

    def __init__(self, path: Path) -> None:
        """Initialize a database inside an operator-controlled private directory."""
        self._path = path
        with self._transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS bindings (
                    conversation_id TEXT PRIMARY KEY,
                    execution_user_id TEXT NOT NULL,
                    customer_ref TEXT NOT NULL,
                    session_id TEXT NOT NULL UNIQUE,
                    expires_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id INTEGER PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    occurred_at REAL NOT NULL
                );
                """)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            db = sqlite3.connect(self._path, timeout=5, autocommit=False)
            try:
                with db:
                    yield db
            finally:
                db.close()
        except sqlite3.Error as error:
            raise BindingStoreUnavailable("Binding store unavailable.") from error

    @staticmethod
    def _audit(db: sqlite3.Connection, event: str, now: datetime) -> None:
        db.execute(
            "INSERT INTO audit_events(event_type, occurred_at) VALUES (?, ?)",
            (event, now.timestamp()),
        )

    def register(
        self,
        *,
        conversation_id: str,
        execution_user_id: str,
        customer_ref: str,
        expires_at: datetime,
        now: datetime,
    ) -> BrokerBinding:
        """Atomically replace the current binding and record the lifecycle event."""
        binding = new_binding(
            conversation_id=conversation_id,
            execution_user_id=execution_user_id,
            customer_ref=customer_ref,
            expires_at=expires_at,
            now=now,
        )
        with self._transaction() as db:
            db.execute(
                """
                INSERT INTO bindings VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    execution_user_id=excluded.execution_user_id,
                    customer_ref=excluded.customer_ref,
                    session_id=excluded.session_id,
                    expires_at=excluded.expires_at
                """,
                (
                    binding.conversation_id,
                    binding.execution_user_id,
                    binding.customer.customer_ref,
                    binding.customer.session_id,
                    binding.expires_at.timestamp(),
                ),
            )
            self._audit(db, "binding_registered_or_replaced", now)
        return binding

    def revoke(self, conversation_id: str) -> None:
        """Remove the active binding and record the revocation atomically."""
        with self._transaction() as db:
            db.execute("DELETE FROM bindings WHERE conversation_id = ?", (conversation_id,))
            self._audit(db, "binding_revoked", datetime.now(UTC))

    def resolve(
        self, conversation_id: str, execution_user_id: str, now: datetime
    ) -> BrokerBinding | None:
        """Resolve an exact, unexpired scope and audit the outcome."""
        with self._transaction() as db:
            row = db.execute(
                """
                SELECT customer_ref, session_id, expires_at FROM bindings
                WHERE conversation_id = ? AND execution_user_id = ? AND expires_at > ?
                """,
                (conversation_id, execution_user_id, now.timestamp()),
            ).fetchone()
            self._audit(db, "context_denied" if row is None else "context_resolved", now)
            if row is None:
                return None
            return BrokerBinding(
                conversation_id,
                execution_user_id,
                VerifiedCustomer(str(row[0]), str(row[1])),
                datetime.fromtimestamp(float(row[2]), UTC),
            )

    def is_active(self, customer: VerifiedCustomer, now: datetime) -> bool:
        """Check session and customer together against the current durable state."""
        with self._transaction() as db:
            row = db.execute(
                """
                SELECT 1 FROM bindings
                WHERE session_id = ? AND customer_ref = ? AND expires_at > ?
                """,
                (customer.session_id, customer.customer_ref, now.timestamp()),
            ).fetchone()
            self._audit(db, "session_denied" if row is None else "session_active", now)
            return row is not None
