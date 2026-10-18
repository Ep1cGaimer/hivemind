"""A tiny retry-safe payment authorization boundary.

The demo intentionally keeps gateway and ledger interfaces explicit. A real
adapter can implement them without changing the idempotency decision made here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequest:
    payment_id: str
    amount: Decimal
    currency: str
    idempotency_key: str
    request_fingerprint: str


@dataclass(frozen=True)
class PaymentResult:
    payment_id: str
    status: str
    gateway_reference: str | None = None
    replayed: bool = False


class PaymentLedger(Protocol):
    def find_by_idempotency_key(self, key: str) -> PaymentRequest | None: ...

    def record_authorization(self, request: PaymentRequest, gateway_reference: str) -> None: ...


class PaymentGateway(Protocol):
    def authorize(self, request: PaymentRequest) -> str: ...


def process_payment(
    request: PaymentRequest,
    ledger: PaymentLedger,
    gateway: PaymentGateway,
) -> PaymentResult:
    """Authorize once, replay safely, and reject key/fingerprint conflicts."""

    if request.amount <= 0:
        raise ValueError("payment amount must be positive")
    if not request.idempotency_key.strip():
        raise ValueError("idempotency key is required")
    if not request.request_fingerprint.strip():
        raise ValueError("request fingerprint is required")

    prior = ledger.find_by_idempotency_key(request.idempotency_key)
    if prior is not None:
        if prior.request_fingerprint != request.request_fingerprint:
            raise ValueError("idempotency key reused with a different request")
        return PaymentResult(request.payment_id, "authorized", replayed=True)

    reference = gateway.authorize(request)
    ledger.record_authorization(request, reference)
    return PaymentResult(request.payment_id, "authorized", reference)
