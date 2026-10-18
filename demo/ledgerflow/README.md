# LedgerFlow demo fixture

LedgerFlow is a synthetic payment-processing repository used to exercise
HiveMind's existing Git bridge without changing HiveMind core behavior.

## What the demo shows

1. **Writer** — a fresh bridge session saves a source-bound finding about
   idempotency-key and request-fingerprint reuse.
2. **Consumer** — another bridge session recalls the finding at the same Git
   commit and receives it as `applicable`.
3. **Challenge** — the generated target receives a new commit changing the
   policy wording.
4. **Stale** — a fresh consumer at that new commit retains the immutable finding
   but marks it `historical_source_changed`; it does not silently reuse stale
   guidance.
5. **Provenance** — the existing `explain` API identifies the two supporting
   source paths and branch binding.

All content is synthetic. The target is intentionally small but models a real
payment boundary: positive amounts, idempotent retries, request fingerprints,
gateway references, and a local authorization ledger. Its checks are standard
library `unittest` tests.

## Commands

Run these from the HiveMind repository root. The default output is ignored under
`.local/ledgerflow/`.

```bash
python -m hivemind.ledgerflow_demo prepare --reset
python -m hivemind.ledgerflow_demo demo
python -m hivemind.ledgerflow_demo inspect
python -m hivemind.ledgerflow_demo smoke
```

Use [`PRESENTER_SCRIPT.md`](PRESENTER_SCRIPT.md) for the recording order, exact
OpenCode prompts, and narration.

PowerShell uses the same commands. To use a different local output directory,
append `--output-root path/to/generated-ledgerflow` after the command; the
directory must be marked by this script before `--reset` will remove it.

`demo`, `inspect`, and `smoke` are self-contained replays: each one resets the
marked generated checkout and starts a fresh in-memory API, so commands do not
depend on a server or token left by a previous command.

The walkthrough starts an ephemeral memory-mode HiveMind API, creates an
ephemeral project and agent token, invokes the shipped `hivemind connect` CLI,
and then uses the existing bridge/API operations. It makes no model calls and
does not write the token or generated repository into tracked fixture files.

## Fixture layout

- `template/` — tracked target-repository source, policy, and unit tests.
- `../../hivemind/ledgerflow_demo.py` — local preparation and walkthrough CLI.
- `../../tests/test_ledgerflow_demo.py` — deterministic end-to-end smoke test.
