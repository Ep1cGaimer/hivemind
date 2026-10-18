from decimal import Decimal
import unittest

from ledgerflow.payments import PaymentRequest, process_payment


class Ledger:
    def __init__(self):
        self.rows = {}

    def find_by_idempotency_key(self, key):
        return self.rows.get(key)

    def record_authorization(self, request, gateway_reference):
        self.rows[request.idempotency_key] = request


class Gateway:
    def __init__(self):
        self.calls = 0

    def authorize(self, request):
        self.calls += 1
        return "gw-1001"


class PaymentTests(unittest.TestCase):
    def request(self, fingerprint="cart-7"):
        return PaymentRequest("pay-7", Decimal("19.99"), "USD", "retry-7", fingerprint)

    def test_retry_replays_without_second_gateway_call(self):
        ledger, gateway = Ledger(), Gateway()
        first = process_payment(self.request(), ledger, gateway)
        second = process_payment(self.request(), ledger, gateway)
        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(gateway.calls, 1)

    def test_reused_key_with_new_fingerprint_is_rejected(self):
        ledger, gateway = Ledger(), Gateway()
        process_payment(self.request(), ledger, gateway)
        with self.assertRaisesRegex(ValueError, "different request"):
            process_payment(self.request("cart-8"), ledger, gateway)


if __name__ == "__main__":
    unittest.main()
