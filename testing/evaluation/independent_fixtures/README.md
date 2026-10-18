# Independent synthetic evaluation preparation

This suite was designed from `goal.md` H1–H10 and J without reading the implementation, previous agent discussions, writer logs, or existing answer fixtures. `EXPECTED_OUTCOMES.json` declares the outcomes before model evaluation. No model or provider calls are made by this suite. All eight cases are **untested with actual OpenCode/Zen** until separately executed and recorded.

The repositories, product requirements and test data are original synthetic fixtures, permitted for use and modification in this project. They contain no real customer data or credentials. This is independent simulated evaluation preparation, not proof of real-user usefulness, demand or adoption.

## Files and separation

- `suite.py` creates tiny Python/Git repositories, changes source context, exports control inputs, plans runs and checks final artifacts.
- `EXPECTED_OUTCOMES.json` and the `PROBES` in `suite.py` are private evaluator keys. Never include them in a model's repository, prompt, memory, notes, or tool output.
- `test_suite.py` tests the fixture harness using reference implementations. Its successful executions are deterministic harness tests, not assistant successes.
- `RUN_RECORD.template.json` lists the evidence and full-cost fields to retain per actual run; null measurements remain unknown rather than becoming zeros.
- `evidence_tools.py` exports sanitized complete memory inventories, checks identical starting source, and conservatively audits actual native writer evidence. See [FAIRNESS.md](FAIRNESS.md) for the exact native-harness contract.
- `notes_control.py` implements a capable source-linked notes comparator with independent provenance indexing, bounded recall, full inspection and lexical search. Its runtime path does not import fixture probes or answer keys.

A generated run has `repo/` plus evaluator-owned `state.json`, `prompts.json` and eventual `outcome.json` **outside** that repository. Give a tested assistant only `repo/`, the selected ordinary task prompt, and its condition's context. Use tool/workspace restrictions that keep the evaluator directory and sibling files inaccessible. This harness does not itself enforce filesystem isolation; merely starting in `repo/` is insufficient if tools can traverse outside it. Real runs should use a separate permitted workspace, not this HiveMind checkout. Never mount the evaluator into the tested environment.

Requires Python 3.10+ and Git; no third-party Python dependencies. Run these examples from the HiveMind root; substitute fresh absolute run paths outside the tested environment.

```powershell
py -3 testing/evaluation/independent_fixtures/suite.py prepare failed_approach C:/eval-private/writer-failed-r1
```

Read the returned writer prompt from the evaluator side. Run it as an ordinary task using **actual OpenCode with OpenCode Zen only**. Capture the complete command, session IDs, model identifier, tool/model costs, logs, and memory revisions. Do not insert an evaluator-authored memory or ask the model to save memory. No simulated subagent can stand in for this model run.

Once the actual writer has done its work, freeze its result and start the consumer transition:

```powershell
py -3 testing/evaluation/independent_fixtures/suite.py advance C:/eval-private/writer-failed-r1
py -3 testing/evaluation/independent_fixtures/suite.py export-control C:/eval-private/writer-failed-r1 --findings C:/eval-private/capture-export.json --output C:/eval-private/notes-input.json
py -3 testing/evaluation/independent_fixtures/suite.py materialize C:/eval-private/writer-failed-r1 C:/eval-private/source-r1
py -3 testing/evaluation/independent_fixtures/suite.py materialize C:/eval-private/writer-failed-r1 C:/eval-private/notes-r1
py -3 testing/evaluation/independent_fixtures/suite.py materialize C:/eval-private/writer-failed-r1 C:/eval-private/hivemind-r1
```

`materialize` clones the identical frozen Git source for each condition and excludes ignored generated files and conversation transcripts. A new repository path must retain the same project/branch identity under the product's documented joining flow; if the product cannot join it, report that defect rather than editing the database. The clone has normal `origin` remote refs; they point to the same commits. The consumer needs a new OpenCode process/session, isolated history and the consumer prompt. Do not give it the writer transcript. The control export contains **unmodified raw findings**, all event metadata, commit parents, refs, exact current source identities, complete historical source content for all branches and source hashes. Give the capable notes control all qualifications, checkpoints, corrections, conflicts, validation evidence and provenance that HiveMind can use. The optional `--findings` argument must be supplied for actual notes comparisons; an omitted argument exports an empty history and must not be used to handicap notes.

Allow a capable notes implementation to index provenance, follow Git changes and select relevant context, with equal source/tool access and comparable context and execution budgets. Do not force it to append every note to the prompt. Charge notes preparation, review and maintenance, and charge HiveMind capture, installation and maintenance equivalently. The source export is an input format; `notes_control.py` supplies the evaluation-only retrieval competitor over a separate complete actual memory inventory. Source-only receives the same source checkout and Git access, with no historical context injection. Its ability to rediscover the answer is legitimate.

Run the independent checker after each completed consumer. It imports the final code in a fresh process and checks artifacts; it does not fix code or run the missing build for a consumer:

```powershell
py -3 testing/evaluation/independent_fixtures/suite.py check C:/eval-private/notes-r1
```

Keep stdout, stderr and `outcome.json` outside model context until the run is finished. Exit 0 means all declared final-artifact probes passed; exit 1 means a probe failed; exit 2 means harness/setup error. These checks are bounded examples, not exhaustive correctness proofs. They do not prove automatic capture, recall timing, database use, graph relationships or usefulness.

## Eight task types

| Case | Actual writer activity needed | Fresh consumer work and objective outcome |
| --- | --- | --- |
| `failed_approach` | Reproduce seeded SQL LIKE mismatch for punctuation in IDs and repair lookup | Implement cart totals; wildcard IDs, absent IDs and injection-shaped strings must behave as exact opaque IDs |
| `build_prerequisite` | Experience missing generated schema, discover/run build and fix decoder types | Implement encoder; rebuild schema in clean checkout and emit typed, schema-ordered compact JSON |
| `branch_constraint` | Implement slug helper on `partner-unicode` | Implement article routes according to Unicode policy; repeat `advance --variant main` on a separate writer replica to test wrong-branch restraint |
| `unfinished_checkpoint` | Interrupt actual normal writer after a meaningful incomplete patch | Finish validated CSV reconciliation and CLI from exact frozen WIP; malformed quantities/duplicates must fail |
| `stale_guidance` | Implement display under half-up policy | `advance` commits half-even policy; implement invoice totals using current per-line rounding |
| `conflicting_interpretations` | Two fresh independent writers inspect contradictory guides | Implement runtime-selectable inclusive/exclusive quotes and source-referencing rationale |
| `integration_applicability` | Implement digest on `transport-v2` | `advance --variant before` tests main v1; `--variant after` creates actual merge, then test v2 bytes and digest |
| `no_history` | None; do not invent prior findings | Implement integer histogram; check correctness, input preservation and unnecessary overhead |

Case-specific requirements:

- Failed-approach and build-prerequisite history qualifies only if the actual writer's execution evidence establishes the attempted failure/discovery. The seeded defect alone does not establish that a writer investigated it. If the writer solves immediately without repeating the bad query or encountering the missing build, preserve the run and mark the relevant historical premise unestablished.
- The checkpoint case requires an external execution/tool budget or interruption after a meaningful incomplete edit. Record the exact stopping rule **before** the writer run. `advance` preserves the tracked work as a fixture commit, but cannot establish that the work was incomplete or that a real checkpoint was captured. A completed writer is invalid for the unfinished-handoff comparison; retain it as such.
- For conflicts, `prompts.json` includes `writer` and `writer_two`. Run the second writer in a fresh workspace at the same writer-start revision, using its own prompt. Retain both independently produced findings and their exact source IDs in the control export and HiveMind input. Do not fabricate the second finding or silently pick a newer interpretation. If actual captured records do not preserve the two incompatible stakeholder interpretations, mark that historical premise unestablished; two source documents alone do not prove conflict capture. Both writers may correctly resolve the conflict immediately, which is legitimate and must be reported. Freeze one code snapshot identically for all conditions. The checker tests both runtime modes in one process, restoring the file afterward. It checks rationale references, not the sophistication of the rationale.
- For branch and integration before/after variants, make separate copies of the **same writer snapshot before advancing**. Use `advance` once per copy with the appropriate variant. Never run a second consumer on an already solved repository. The pre-integration consumer may correctly implement v1 even though v2 history is inspectable; inclusion and qualification of v2 findings requires separate recall inspection.
- Integration advance creates a real no-fast-forward Git merge. The packet checker independently reconstructs both wire formats rather than trusting a potentially broken serializer. Actual graph-path inspection and relationship ablation need the product's live tests; Git history alone cannot pass those gates.
- Consumer edits to policy/config/transport must be reviewed against the frozen consumer-start revision. Changing requirements to make tests pass invalidates the run. The checker intentionally toggles runtime tax mode, so hardcoding the initial setting fails.

## Repetition, cost and limits

```powershell
py -3 testing/evaluation/independent_fixtures/suite.py plan --seed 1729 --output testing/evaluation/independent_fixtures/run-plan.json
py -3 -m unittest discover -s testing/evaluation/independent_fixtures -p test_suite.py -v
```

The plan randomizes 8 distinct tasks × 3 conditions × 3 repetitions = 72 consumer runs. Applicability variants and extra writer sessions are additional reported runs. For each repetition, do one actual writer history (where needed), then use identical frozen sources and historical facts across conditions. Randomize **consumer execution** order; generate new session IDs/workspaces and never reuse an assistant conversation. All conditions use the same recorded Zen model/version, source access and declared budgets. Choose budgets before execution; a timeout, setup repair, permission interruption or failed writer is recorded, never silently discarded.

For every run record setup, expected-outcome version/hash, command, fixture commit and working snapshot, task/condition/repetition, writer and consumer IDs, memory/context/revision IDs, raw logs, actual outcome, all interventions, wall time, model input/output/cached tokens, tool counts/time, capture/recall time, and preparation/review/maintenance effort. Label simulated review effort separately from measured human effort. Retain failures and report medians/distributions per task as well as totals. No claim of a 20% improvement is justified without actual comparable measurements and maintained quality.

The fixtures can measure final-code correctness and changes in repeated investigation, context consumption and handoff effort when coupled to actual logs. They can reveal regressions from stale, conflicting or wrong-branch guidance and overhead on no-history work. They cannot by themselves prove real-human usability, willingness to pay, production reliability, automatic lifecycle behavior or a competitive advantage over capable notes. These are deliberately tiny tasks; ceiling effects and easy source rediscovery may produce ties. Report those ties. No forced baseline failure is built in.
