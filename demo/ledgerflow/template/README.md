# LedgerFlow payment-processing target

LedgerFlow is a deliberately small synthetic payment service used by the
HiveMind demo. It models the part of a payment system that is easy to get wrong
when a retry crosses a process boundary: an authorization must be paired with
one stable idempotency key and one request fingerprint.

The implementation is dependency-free Python. From the target root, run its
local checks with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
```

On PowerShell, use `$env:PYTHONPATH = "src"` before the same Python command.

The policy in `docs/payment-policy.md` is source material for the LedgerFlow
HiveMind walkthrough. The demo changes that policy in a later Git commit so a
fresh consumer can see the original writer finding become stale instead of
treating it as current guidance.
