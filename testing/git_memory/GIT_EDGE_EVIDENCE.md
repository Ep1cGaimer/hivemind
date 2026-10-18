# Independent Git acceptance edge evidence — 18 October 2026

These are deterministic fixtures with real local Git, specified before their first
execution. No model sessions are involved. The live class creates a random new
FalkorDB graph and fresh projects, retains that graph, and never resets existing
graphs or changes an existing service or container. Production files and the
OpenTelemetry patch are outside this agent's edit scope.

## Independently fixed expectations (before first run)

| ID | Fixture and expected result |
| --- | --- |
| D2 | Two bounded, divergent branches omit their real common ancestor A. Save new feature learning at B2, then deepen without advancing either tip. Discover A and prove its source matches, but create no publication edge and return no feature learning on main. |
| D5 | Save two pending findings. A foreign-authored successor publishes neither. An own-authored successor changes one required source; only the unchanged-source finding receives exactly one `PUBLISHES` edge from that successor with reason `authored_commit` and the exact qualifying observation receipt. Original source commit remains distinct. |
| D7 | Real conflicting merge retains one of two required sources and deliberately resolves the other using destination content. The source tip is a real ancestor, but the finding gets `needs_review/source_mismatch`, no publication and no inherited recall; historical finding and both bindings remain. |
| D13 | Delete the only required source and commit. Current recall labels the retained finding `historical_source_changed`, with one required/bound source and zero matches. Recall at the historical context remains applicable. |
| D19 | Execute an actual Git branch switch with a different commit and identical source content between hash/history and history/status stages. Both injected races must reject a changed checkout, returning zero torn observations. |
| D20 | A fixture-owned, required clean/smudge filter replaces a non-newline token. Distinct worktree/blob bytes must share the actual committed canonical source identity; canonical/raw/smudged forms remain clean and fully applicable. |
| E8 | Create 1025 eligible findings (one beyond the real page limit). Recall must state incomplete candidates, stay under eight findings/8000 serialized characters, and expose truncation. Live recall uses bounded fixed repository queries and no generic node/edge download. Separately, 1025 additional retained observation fixtures must block new integration with explicit `integration_observations_incomplete` and no unqualified inheritance. |

## Execution record

Test artifact: `tests/test_git_acceptance_edges.py`.

| Run | Actual result |
| --- | --- |
| First offline invocation | **passed**: 15 discovered, 8 passed, 7 explicit live skips; 20.193 s. |
| First live opt-in invocation | **failed**: 14/15 passed, 1 test-harness assertion failure, no skips; 60.142 s. Retained graph: `hivemind_git_edges_3274ba250ae02844aa1cc8e3`. |
| Corrected live opt-in invocation | **passed**: 15/15, no skips; 62.737 s. Retained graph: `hivemind_git_edges_3bc885af0d6e64da090b22ce`. |

The first live candidate-overload test completed recall, then its instrumentation
incorrectly rejected the legitimate singleton `node_lookup` used to read the
project/context. The recorded query set was:

```text
AssertionError: False is not true : {'git_excluded', 'git_candidates',
'git_revisions', 'git_applicability', 'node_lookup'}
```

This is a test-harness defect, not evidence of an unbounded product download. The
test now allows `node_lookup` only with a singleton string `id` parameter while
continuing to reject generic node/edge downloads. All original expected product
outcomes and the real 1024-record page limit remain unchanged.

Durations will be whole-suite wall time, not recall p95 or plugin overhead.
Cold/warm performance and all model-dependent gates remain outside these fixtures.
