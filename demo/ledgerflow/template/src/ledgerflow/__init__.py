"""Small dependency-free payment-processing example for the HiveMind demo."""

from .payments import PaymentRequest, PaymentResult, process_payment

__all__ = ["PaymentRequest", "PaymentResult", "process_payment"]
