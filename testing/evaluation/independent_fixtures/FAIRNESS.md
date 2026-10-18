# Native-evaluation input contract and independent evidence checks

These rules apply before actual consumer evaluation. No future outcome was used to define them. The native execution harness is separate; these helpers make no service/model calls and cannot authenticate a log or database export on their own.

## Full memory export is different from recall

`evidence_tools.py notes` consumes an **authoritative full scoped inventory**, not an adapter recall response:

```json
{
  "records": ["every full record_to_dict(GitRecord), not a summary"],
  "links": [
    {"edge_type":"SUPPORTED_BY","from_id":"finding-id","to_id":"source-id","properties":{}}
  ],
  "inventory": {
    "complete":true,
    "all_kinds":true,
    "filters":{"workspace_project_id":"actual-project-id","repo_id":"actual-repository-id"},
    "captured_at":"actual export time before first consumer",
    "pages":"actual cursor/count/completeness receipts from native exporter"
  }
}
```

The strings in the example are schema descriptions, not valid records. Each actual record retains **all** fields, including `id`, `kind`, `key`, tenant/project/repository identities, `branch_id`, `head`, `snapshot_id`, author, session, timestamps, all `data`, origin contexts, source identities, classifications, corrections and supersession IDs. Include all source, observation, snapshot, branch, commit, publication and revision records needed to interpret the findings/checkpoints, along with all scoped relationship properties. Enumerate all kinds and paginate until complete. A bounded/truncated page must never become `complete:true`. The helper rejects absent endpoint records, duplicate IDs, non-scope filters and incomplete inventories; it cannot independently verify that a caller's completeness declaration is true.

Do not filter by current branch, HEAD, current source match, writer session, latest revision, active status, relevance score or publication reachability. Historical, excluded, stale, WIP, superseded and conflicting records must survive. Timestamps are evidence, not a truth selector. Retain exclusion reasons and applicability assessments when present; absence of such a field must remain absence. Additional schema fields and arrays are preserved, not silently dropped by an allowlist.

The output has `full_inventory`, a simple ID-by-kind index and a sanitization manifest. It performs no retrieval, summary, ranking or adjudication. A separately recorded recall response may be included in the raw inventory as observational metadata, but cannot substitute for the full record set. A strong notes control gets the complete sanitized inventory and full source/history export and can index/query them with a tool. It need not fit every record into the initial model prompt. Match the adapter's delivered context cap and retrieval budget; allow ordinary source/Git inspection equally. If the control can match graph behavior with its own provenance index, report that as a legitimate tie or success.

```powershell
py -3 testing/evaluation/independent_fixtures/evidence_tools.py notes --input C:/eval-private/full-inventory.json --policy C:/eval-private/redaction-policy.json --output C:/eval-private/complete-notes.json
```

The optional policy is evaluator-private JSON containing `secret_values` and `private_prefixes` arrays; never put secret literals in command arguments. By default credential fields such as authorization/password/access_token are redacted while `tokens` usage metadata and GitRecord `key` survive. Explicit secret values are removed from arbitrary strings. Configured private source paths and associated content are redacted with an explicit manifest. All IDs, qualifiers, status/exclusion/revision metadata and relationship counts survive unless an actual ID itself contains an explicitly configured secret. The helper does not claim general secret detection. The synthetic fixtures need no secret source data. Apply exactly the same policy to all conditions; captured private data remains a privacy defect, and sanitizing the control alone cannot repair it or make an unequal comparison fair. Audit raw inventories/logs privately for leakage before distribution.

## Identical starting source and history

For each task/repetition, perform actual writer work once. Save the actual writer logs, automatic captures and source snapshot. For conflicts, perform the second independent writer at the same initial revision and keep both actual histories. Commit the meaningful writer state once, let the native bridge observe that authored commit, then apply the fixture's declared branch/source/integration transition. Freeze the memory inventory **before** the first consumer. Use the same frozen source, history, findings and metadata in all three conditions. Do not reuse a consumer conversation or let earlier consumers' new captures enter later consumers' starting context.

`suite.advance(args, after_freeze=callback)` offers a native-harness observation boundary. Its callback signature is `callback(repo: pathlib.Path, writer_tip: str)`. It runs after the actual writer commit exists and before any checkout, rounding-policy edit, generated-file removal or merge. It may let the actual bridge observe and publish that authored source. A callback exception aborts without branch/source transition; the real freeze event is persisted and a clean retry reuses the same commit. The observer may not modify tracked source or change HEAD. The CLI exposes no callback and makes no publication claim. Record the actual observation/publication result separately.

Then materialize three fresh Git clones. `suite.materialize` checks out with `core.autocrlf=false`, preserving source bytes on Windows. Every condition must have the same HEAD, branch, tracked contents/modes, other application source files, semantic branch tips and reachable commit set. Normal clone `origin/branch` aliases are normalized for this comparison. Build artifacts are absent in all build consumers; no condition inherits a writer's ignored generated schema. All conditions retain Git source/history access.

```powershell
py -3 testing/evaluation/independent_fixtures/evidence_tools.py snapshot --repo C:/condition/repo --runtime-path opencode.json --runtime-path .hivemind --output C:/eval-private/source-condition.json
```

The three `source_snapshot_sha256` values must match immediately before their consumers launch, after explicit runtime exclusions. Exclusions must be specific repository-relative paths, identical across conditions; they may not overlap tracked source. Python bytecode is ignored. Other untracked or ignored application files remain in the digest, so a prebuilt schema or accidental answer file changes the starting snapshot. Store the manifest privately; the helper does not copy source into model context.

Runtime configuration is separately recorded and compared: same installed OpenCode2/Zen version and model ID, source/tool permissions, task prompt, working directory semantics, budgets and fresh-session policy. Condition differences consist only of the declared memory interface. No credentials, evaluator probes, answer keys, writer transcript or implementation history are accessible to any tested assistant. Native permissions must prevent traversal outside the test workspace; working directory selection alone does not enforce this. A fixture-harness helper cannot certify the runtime sandbox.

Consumer source/policy authority must remain frozen. The independent outcome checker rejects edits to contracts/policies/transport that weaken requirements. New helper checks also reject writer edits to those source authorities. A final-code timeout is a failed artifact check, not a successful model result or a silent setup skip.

## Actual writer historical-premise audit

```powershell
py -3 testing/evaluation/independent_fixtures/evidence_tools.py audit-writer --run C:/eval-private/frozen-task --log C:/eval-private/writer.jsonl --inventory C:/eval-private/full-inventory.json --receipt C:/eval-private/writer-review.json --output C:/eval-private/writer-premise.json
```

Use repeated `--log` for actual writer sessions. Native tool events have `type=tool_use`, `sessionID`, `part.id`, `part.tool`, and `part.state` with completed status, input, output, time and metadata exit code. The helper accepts integer `metadata.exit`, `metadata.exit_code`, `metadata.exitCode` or `state.exit_code`. Completed tool status without a recorded shell exit code is **not** proof of successful validation. Assistant narrative saying tests passed is not execution evidence. Raw file hashes, session IDs and line/part IDs make each machine anchor inspectable.

The audit checks independent frozen-writer functional probes, actual execution anchors and source bindings from structured source identities/`SUPPORTED_BY` links. A body merely mentioning a filename does not establish source binding. It never generates a missing history, finding or checkpoint. For the decoder probe the evaluator builds only a private scratch copy to check semantics; this is explicitly not evidence that the real writer discovered the build.

| Case | Machine evidence required, in addition to a correct frozen writer artifact |
| --- | --- |
| Failed approach | Actual Python lookup/demo output shows the seeded wrong price before a later successful lookup validation; saved finding binds catalog source |
| Build prerequisite | Actual missing-schema traceback, later successful generator command and successful decoder validation in order; saved finding binds relevant source |
| Branch constraint | Actual successful slug validation; writer source policy is Unicode; finding binds policy source |
| Checkpoint | Meaningful AST change, parser milestone works, full task still fails, separate actual checkpoint, matching actual stop event and unchanged source across capture |
| Stale guidance | Actual successful old display validation; saved finding binds old money policy; declared consumer source changes to half-even |
| Conflicting interpretations | At least two distinct captured writer sessions and both guide source identities; actual preview validation; semantic review confirms incompatible qualified interpretations were retained |
| Integration | Actual digest validation and transport source binding; feature remains unintegrated for before variant or is actually reachable through a merge for after variant |
| No history | No writer session/log and no historical finding/checkpoint in the complete starting inventory |

Machine command anchors are conservative evidence locations, not proof of reasoning, test coverage or authenticity. A keyword match is insufficient for the full historical premise. An independent simulated review must inspect actual records, their qualifications and anchored execution evidence. Its optional receipt has `independent_review` with `kind: independent_simulated_review`, actual `reviewer_id`, reviewed `record_ids`, and `all_listed_questions_satisfied:true`. The reviewer must differ from writer session IDs. Do not populate that receipt until review actually occurs. The output includes the precise review questions. A missing/failed anchor or absent review leaves status `untested`/mechanically `unestablished`, never a fabricated pass. Retain and report writer failures as well as consumer failures.

## Checkpoint stop design

Predeclare the stop rule, writer budget and maximum attempts before starting. A suitable bounded rule is: at each completed source-edit tool boundary, use evaluator-private read-only checks; stop at the first meaningful `reconcile.py` AST change for which the parser milestone passes and the full task remains incomplete. If a single writer edit completes the entire tool, the run does not qualify as an unfinished handoff. Preserve that outcome; do not delete code, insert TODOs, rewrite the prompt to manufacture incompleteness or quietly retry until a convenient result appears. A completed writer may be reported separately, outside the checkpoint comparison.

Cancel/pause the actual native writer at that tool boundary through its supported lifecycle, retaining the emitted tool event and exact source snapshot. Permit the product's actual bounded automatic capture/finalization lifecycle, without an evaluator-authored summary or manual memory write. Verify that source bytes remain unchanged while the automatic checkpoint is captured. Freeze that same source for every condition. If native cancellation does not produce an automatic checkpoint, retain the failure; a notes author may not silently fill in a checkpoint on HiveMind's behalf. If a separately prepared notes handoff is part of the control design, preserve its same facts/metadata and charge its preparation/review effort explicitly.

The private `checkpoint_stop` receipt records actual `rule`, `declared_before_writer:true`, `actual_stop_event_part_id`, `writer_frozen_commit`, `source_digest_before_capture` and `source_digest_after_capture`. The native runner must retain the predeclaration artifact/time and actual hashes; a boolean declaration alone cannot prove timing. The audit verifies the selected actual event and source/commit matching. Actionability remains a separate independent simulated semantic review of actual checkpoint `data.body`, not a required invented `next_steps` schema.

For all cases, exact matching source/metadata and independent correctness are necessary; retrieval success alone does not establish benefit. Keep all 72 consumer runs and their writer prerequisites, failures, exclusions, preparation costs and interventions. Unsupported historical premises and unavailable model runs remain unestablished. Tiny source-recoverable tasks may tie across all three conditions, and that is an honest result.
