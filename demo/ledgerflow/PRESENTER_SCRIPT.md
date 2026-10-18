# LedgerFlow demo presenter script

This is the recording script for the HiveMind hackathon demo. It is written for
PowerShell on Windows, but the commands are the same in a Unix shell with the
usual path and environment-variable syntax changes.

## The story

LedgerFlow processes payments. A payment authorization can time out after the
provider has accepted it, so a retry must reuse the same idempotency key and
request fingerprint. A previous coding agent discovers that constraint. A fresh
agent later proposes a generic retry wrapper, but HiveMind recalls the earlier
source-linked finding and makes the agent reconsider.

The graph proof also shows that the finding becomes historical when its policy
source changes. This is the important distinction from a plain notes file:
HiveMind remembers the finding together with its Git applicability and evidence.

## Before recording

From the HiveMind checkout, run the deterministic rehearsal once:

```powershell
python -m hivemind.ledgerflow_demo smoke
python -m hivemind.ledgerflow_demo inspect
```

Both commands should return JSON containing `"ok": true`.

The first command proves the assertions. The second prints the finding ID,
source paths, source hashes, branch binding, and the
`historical_source_changed` result after the policy challenge.

For the native OpenCode portion, also make sure the following are ready:

- HiveMind server running at `http://127.0.0.1:8000`;
- a HiveMind project and project token created through **Connect agent**;
- `npm ci` completed in the HiveMind checkout;
- `HIVEMIND_OPENCODE_BIN` pointing at the pinned OpenCode executable;
- the OpenCode Zen model `opencode/deepseek-v4.1-flash-free` available.

From the HiveMind checkout, the pinned client setup is:

```powershell
npm ci
$env:HIVEMIND_OPENCODE_BIN = (Resolve-Path .\node_modules\@opencode\cli\bin\opencode.exe).Path
```

Keep this PowerShell session open while you run the native scenes. The
generated target repository can be opened in a second terminal, but it must use
the same activated Python environment (or the HiveMind checkout's `.venv` Python).

## Recording script

### Scene 1 — Introduce the problem (20 seconds)

**Do:** Show the LedgerFlow fixture folder or open these two files:

```text
demo/ledgerflow/template/src/ledgerflow/payments.py
```

**Say:**

> “This is LedgerFlow, a small payment-processing service. The dangerous case
> is a timeout: the provider may have accepted the charge even though the
> response was lost. So retrying with a new request can charge the customer
> twice. The repository policy says the retry must preserve the idempotency key
> and request fingerprint.”

Do not spend time explaining every file. The audience only needs to understand
the constraint that the agents must carry forward.

### Scene 2 — Show the graph proof (35 seconds)

**Do:** Run:

```powershell
python -m hivemind.ledgerflow_demo inspect
```

If the JSON is too large for the recording, pipe it to a file first and show the
important fields from the output. The meaningful values are:

```text
writer.source_paths
provenance.source_bindings
provenance.branch_path
stale.applicability = historical_source_changed
```

**Say:**

> “The first agent’s finding is not just free-floating text. HiveMind attached
> it to the exact Git observation and these two source files. It can explain the
> branch relationship and the source hashes. After the policy source changes,
> the old finding is retained, but it is marked historical and requires
> verification instead of being silently treated as current truth.”

**Do:** Briefly point to the graph implementation:

```text
hivemind/git_queries.py
hivemind/git_graph.py
HIVEMIND_GRAPH_CONTRACT.md
```

**Say:**

> “The graph is useful here because it checks branch ancestry and source
> applicability. A normal notes file could store the warning, but it would not
> know whether this checkout still matches the source that created it.”

### Scene 3 — Prepare the target for native OpenCode (20 seconds)

**Do:** Generate a clean target repository:

```powershell
python -m hivemind.ledgerflow_demo prepare --reset
```

Then enter it:

```powershell
Set-Location .local\ledgerflow\repo
```

Connect it using the project ID and token from the HiveMind UI:

```powershell
$env:HIVEMIND_AGENT_TOKEN = "YOUR_PROJECT_TOKEN"
python -m hivemind connect `
  --repo . `
  --url http://127.0.0.1:8000 `
  --project project:YOUR_PROJECT_ID `
  --remote https://example.invalid/ledgerflow-demo.git `
  --client opencode
```

**Say:**

> “This is a fresh checkout. I connect it once to the HiveMind project. The
> project plugin and Git-private bridge state are created locally; the token is
> not committed to the target repository.”

### Scene 4 — Agent A writes the finding (45–60 seconds)

**Do:** Run the managed OpenCode command:

```powershell
python -m hivemind run `
  --repo . `
  --model opencode/deepseek-v4.1-flash-free `
  --format json `
  "Inspect the LedgerFlow payment path. Do not edit files. Find the most important retry safety constraint for a future engineer, cite the exact source files, and preserve the condition under which the rule applies."
```

Show the model’s answer and then:

```powershell
python -m hivemind status --repo .
```

**Say:**

> “This is Agent A. It has finished its investigation. HiveMind’s bounded
> capture pass records the useful finding with the current Git context and
> source paths. The chat session can now disappear; the project memory remains.”

If the model records a no-change receipt instead of a finding, do not improvise.
Use the deterministic `inspect` result as the graph evidence and describe this
native segment as an attempted agent pass. For the guaranteed finding, the
deterministic bridge rehearsal is the source of truth.

### Scene 5 — Agent B starts cold (45–60 seconds)

**Do:** Start a completely new PowerShell process or a fresh terminal session.
Return to the generated target repository and run:

```powershell
python -m hivemind run `
  --repo . `
  --model opencode/deepseek-v4.1-flash-free `
  --format json `
  "You are a new engineer with no previous chat. Plan a safe implementation of a retry wrapper for LedgerFlow's failed HTTP requests. First inspect any applicable HiveMind project context. Distinguish payment authorization requests from read-only requests, and explain which operations may be retried. Do not edit files yet."
```

**Say:**

> “This is a fresh process. It has no access to Agent A’s conversation. Before
> planning, HiveMind supplies only the project context that applies to this
> checkout.”

Pause when the model mentions the idempotency-key constraint.

### Scene 6 — The dangerous alternative (35–45 seconds)

**Do:** In another fresh process, run:

```powershell
python -m hivemind run `
  --repo . `
  --model opencode/deepseek-v4.1-flash-free `
  --format json `
  "I want to add one generic retry wrapper around every failed HTTP request in LedgerFlow. Evaluate this approach against the repository and any applicable HiveMind memory. If it is unsafe, stop and propose the smallest safer design instead. Do not edit files."
```

**Say:**

> “This is the second direction of the demo. The new engineer proposes a
> different implementation method. HiveMind surfaces the previous warning at
> the exact payment boundary, so the agent rejects a blind retry of charge
> requests and separates idempotent reads from payment authorization.”

Use “rejects” or “reconsiders,” not “HiveMind blocked the edit.” HiveMind is an
advisory memory layer in this demo, not a hard policy gate.

### Scene 7 — Close with the graph advantage (20 seconds)

**Say:**

> “The point is not that HiveMind stores more notes. The point is that it stores
> project memory with Git identity and source applicability. A new agent gets the
> warning when it is relevant, can inspect where it came from, and is warned when
> the supporting source has changed.”

Finish by showing:

```text
README.md
DEMO.md
HIVEMIND_GRAPH_CONTRACT.md
hivemind/git_queries.py
```

## Claims to avoid

Do not say:

- “HiveMind prevents the agent from editing code.”
- “The model always saves a finding.”
- “The graph proves the finding is objectively true.”
- “This is a benchmark showing superiority over all notes systems.”

Say instead:

- “HiveMind recalls Git-applicable project memory before a task.”
- “The managed OpenCode path performs a bounded capture pass.”
- “The graph provides provenance and source-change detection.”
- “The demo shows a realistic handoff and stale-guidance warning.”

## Emergency fallback

If the model provider is slow or unavailable, record Scenes 1, 2, 3, and 7.
The deterministic command below is sufficient to show the working graph behavior:

```powershell
python -m hivemind.ledgerflow_demo demo
```

It proves the writer, cold consumer, source challenge, stale recall, provenance
bindings, and privacy assertions without making a model call.
