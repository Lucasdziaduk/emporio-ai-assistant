"""Local customer verification and short-lived order access grants."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock

from pydantic import SecretStr, ValidationError

from app.data.repositories import CustomerRepository, OrderRepository
from app.domain.errors import AuthenticationFailedError
from app.domain.schemas import OrderVerificationRequest


@dataclass(frozen=True)
class OrderAccessGrant:
    """Short-lived proof that one order was verified in one session."""

    order_id: int
    session_id: str
    issued_at: datetime
    expires_at: datetime

    def is_valid_for(
        self,
        order_id: int,
        session_id: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return (
            self.order_id == order_id
            and self.session_id == session_id
            and self.issued_at <= current < self.expires_at
        )


class IdentityService:
    """Verify a supplied phone against the customer attached to an order.

    Phone values are validated and compared locally. They are never returned
    from this service and must not be passed to the LLM provider or logs.
    """

    def __init__(
        self,
        customer_repository: CustomerRepository,
        order_repository: OrderRepository,
        *,
        auth_ttl_minutes: int = 10,
        max_attempts: int = 3,
    ) -> None:
        if auth_ttl_minutes < 1 or max_attempts < 1:
            raise ValueError("Authentication limits must be positive.")
        self.customer_repository = customer_repository
        self.order_repository = order_repository
        self.auth_ttl = timedelta(minutes=auth_ttl_minutes)
        self.max_attempts = max_attempts
        self._failed_attempts: dict[str, int] = {}
        self._lock = RLock()

    @staticmethod
    def normalize_phone(phone: str | SecretStr) -> str:
        raw = phone.get_secret_value() if isinstance(phone, SecretStr) else phone
        if not isinstance(raw, str):
            return ""
        return re.sub(r"\D", "", raw)

    def attempts_remaining(self, session_id: str) -> int:
        with self._lock:
            return max(0, self.max_attempts - self._failed_attempts.get(session_id, 0))

    def verify_order_access(
        self,
        order_id: int,
        phone: str | SecretStr,
        *,
        session_id: str,
        now: datetime | None = None,
    ) -> OrderAccessGrant:
        """Verify phone ownership and return an order/session-scoped grant."""
        if not session_id.strip():
            raise ValueError("session_id cannot be empty.")

        with self._lock:
            failures = self._failed_attempts.get(session_id, 0)
            if failures >= self.max_attempts:
                raise AuthenticationFailedError()

            try:
                request = OrderVerificationRequest(order_id=order_id, phone=phone)
            except ValidationError:
                self._failed_attempts[session_id] = failures + 1
                raise AuthenticationFailedError() from None

            # Use the same generic response for nonexistent orders and mismatches
            # to avoid disclosing whether an order ID exists.
            customer_id = self.order_repository.get_customer_id(request.order_id)
            customer = self.customer_repository.get_by_id(customer_id) if customer_id else None
            supplied_digits = self.normalize_phone(request.phone)
            registered_digits = self.normalize_phone(customer.phone) if customer else ""

            if not customer or not supplied_digits or supplied_digits != registered_digits:
                self._failed_attempts[session_id] = failures + 1
                raise AuthenticationFailedError()

            self._failed_attempts.pop(session_id, None)
            issued_at = now or datetime.now(timezone.utc)
            if issued_at.tzinfo is None:
                issued_at = issued_at.replace(tzinfo=timezone.utc)
            return OrderAccessGrant(
                order_id=request.order_id,
                session_id=session_id,
                issued_at=issued_at,
                expires_at=issued_at + self.auth_ttl,
            )
