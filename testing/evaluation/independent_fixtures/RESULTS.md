# Preparation and deterministic harness results

Date: 2026-10-18. Scope: independent synthetic evaluation preparation.

Only `goal.md` was read before defining the expected outcomes. No HiveMind implementation, prior agent conversations, writer logs or earlier answer fixtures were inspected. All authored files are confined to this new directory. Production files and the OpenTelemetry work were not changed. No model/provider call was made.

`EXPECTED_OUTCOMES.json` was created before any fixture validation or model evaluation. It defines eight distinct task outcomes and required historical premises. `run-plan.json` records a seed-1729 randomized plan for 72 consumer evaluations, plus separately reported applicability variants and writer runs. All actual model-run statuses remain **untested**.

Executed:

```text
py -3 -m unittest discover -s testing/evaluation/independent_fixtures -p test_suite.py -v
Ran 5 tests in 14.522s — OK (final run)
```

The five harness tests cover:

- All eight untouched consumer stubs fail, and external reference implementations pass the declared final-artifact probes.
- Encoder implementation still fails without a consumer-generated schema; the checker does not build it on the consumer's behalf.
- Built encoder and writer-repaired decoder complete a typed round-trip; generated schema is a requirement of the runnable application, not merely an evaluator side effect.
- Wrong-branch Unicode behavior and pre-integration v1 behavior pass with their appropriate reference implementations.
- Policy changes that weaken the consumer's task are rejected.
- Notes export preserves a supplied structured finding without changing qualifications/source/revision metadata, includes actual merge parents, and excludes evaluator files. Fresh condition materialization preserves HEAD and excludes evaluator outcomes.
- The plan has 72 distinct sessions and nine consumer evaluations per distinct task, balanced across three conditions.

These are deterministic tests of the fixture harness, not real writer/consumer sessions, automatic memory integration, behavioral benefit, or product acceptance. Synthetic transition markers and reference code in `test_suite.py` must never be presented as model observations. No performance or usefulness advantage is claimed.

An earlier harness run also passed all five tests in 15.001 seconds. The final run followed an added encoder/decoder round-trip probe. No harness-test failure was discarded.

Evidence still required: actual OpenCode/Zen writer discoveries; genuine unfinished writer interruption; two independent conflict interpretations; automatic capture and fresh-session recall; equally capable notes preparation; complete cost/log collection; actual model final artifacts and all failures; live graph inspection/ablation; simulated usability or adversarial product interaction. The suite makes no real-human claims.
