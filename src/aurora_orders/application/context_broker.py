"""Process-local broker for pre-authenticated synthetic channel bindings."""

import secrets
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Protocol

from aurora_orders.application.customer_sessions import OPAQUE_ID, VerifiedCustomer


@dataclass(frozen=True, slots=True)
class BrokerBinding:
    """Trusted registration data; no bearer credential is stored."""

    conversation_id: str
    execution_user_id: str
    customer: VerifiedCustomer
    expires_at: datetime


class BindingStoreUnavailable(RuntimeError):
    """The binding store cannot safely decide authorization."""


class BindingStore(Protocol):
    """Lifecycle contract for the in-memory and durable broker stores."""

    def register(
        self,
        *,
        conversation_id: str,
        execution_user_id: str,
        customer_ref: str,
        expires_at: datetime,
        now: datetime,
    ) -> BrokerBinding:
        """Register a trusted binding."""
        raise NotImplementedError

    def revoke(self, conversation_id: str) -> None:
        """Invalidate a binding."""
        ...

    def resolve(
        self, conversation_id: str, execution_user_id: str, now: datetime
    ) -> BrokerBinding | None:
        """Resolve a scoped binding."""
        ...

    def is_active(self, customer: VerifiedCustomer, now: datetime) -> bool:
        """Check current session authorization."""
        ...


def new_binding(
    *,
    conversation_id: str,
    execution_user_id: str,
    customer_ref: str,
    expires_at: datetime,
    now: datetime,
) -> BrokerBinding:
    """Validate trusted registration and allocate a new session identifier."""
    if (
        not all(
            OPAQUE_ID.fullmatch(value)
            for value in (conversation_id, execution_user_id, customer_ref)
        )
        or expires_at.tzinfo is None
        or now.tzinfo is None
        or expires_at <= now
    ):
        raise ValueError("Invalid trusted binding.")
    return BrokerBinding(
        conversation_id,
        execution_user_id,
        VerifiedCustomer(customer_ref, secrets.token_hex(24)),
        expires_at,
    )


class ContextBroker:
    """Reference lifecycle store; registration is internal, never an HTTP action."""

    def __init__(self) -> None:
        """Initialize a process-local store."""
        self._bindings: dict[str, BrokerBinding] = {}
        self._lock = Lock()

    def register(
        self,
        *,
        conversation_id: str,
        execution_user_id: str,
        customer_ref: str,
        expires_at: datetime,
        now: datetime,
    ) -> BrokerBinding:
        """Register a pre-authenticated binding, replacing any previous session."""
        binding = new_binding(
            conversation_id=conversation_id,
            execution_user_id=execution_user_id,
            customer_ref=customer_ref,
            expires_at=expires_at,
            now=now,
        )
        with self._lock:
            self._bindings[conversation_id] = binding
        return binding

    def revoke(self, conversation_id: str) -> None:
        """Remove a binding; previously issued sessions no longer resolve."""
        with self._lock:
            self._bindings.pop(conversation_id, None)

    def resolve(
        self, conversation_id: str, execution_user_id: str, now: datetime
    ) -> BrokerBinding | None:
        """Resolve only the exact registered runtime scope."""
        with self._lock:
            binding = self._bindings.get(conversation_id)
            if (
                binding is None
                or binding.execution_user_id != execution_user_id
                or binding.expires_at <= now
            ):
                return None
            return binding

    def is_active(self, customer: VerifiedCustomer, now: datetime) -> bool:
        """Reject unregistered, replaced, revoked or expired sessions."""
        with self._lock:
            return any(
                binding.customer == customer and binding.expires_at > now
                for binding in self._bindings.values()
            )
