# LedgerFlow payment policy

## Retry-safe authorization

The payment gateway may retry an authorization after a timeout. Retries must
reuse the same idempotency key and the same request fingerprint. A different
fingerprint under an existing key is a conflict and must not create a second
authorization.

## Capture boundary

Authorization records are local LedgerFlow state until a separate capture step
confirms the gateway result. A timeout is not proof that an authorization was
declined; reconcile the gateway reference before retrying with new input.

This policy is synthetic demo material and is not a production payment or
compliance policy.
