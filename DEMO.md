# Hackathon Demo

## Product in one sentence

HiveMind gives OpenCode Git-aware shared memory: it recalls applicable findings
before a task and records a finding, checkpoint, or explicit no-change receipt
after the task.

## Live demo

Assume the HiveMind server and FalkorDB are already running.

1. Clone a GitHub repository and enter it:

   ```powershell
   git clone https://github.com/YOUR_USER/YOUR_REPO.git
   Set-Location YOUR_REPO
   ```

2. Connect it to a HiveMind project using the project token from **Connect agent**:

   ```powershell
   $env:HIVEMIND_AGENT_TOKEN = "PROJECT_TOKEN"
   python -m hivemind connect `
     --repo . `
     --url http://127.0.0.1:8000 `
     --project project:YOUR_PROJECT_ID `
     --client opencode
   ```

3. Run a writer session:

   ```powershell
   python -m hivemind run `
     --repo . `
     --model opencode/deepseek-v4.1-flash-free `
     "Review this repository and identify one important implementation constraint."
   ```

4. Run a fresh consumer session:

   ```powershell
   python -m hivemind run `
     --repo . `
     --model opencode/deepseek-v4.1-flash-free `
     "Use the shared project memory and explain how I should safely continue this work."
   ```

5. Show the saved result:

   ```powershell
   python -m hivemind status --repo .
   ```

The important moment is that the second OpenCode process receives the first
session's Git-bound finding before making its decision.

## Requirement mapping

| Hackathon requirement | Repository evidence |
| --- | --- |
| Public source repository | Publish this repository without `.env`, tokens, or `.local/` artifacts |
| README and setup | `README.md` |
| Graph data model | `HIVEMIND_GRAPH_CONTRACT.md` |
| Cypher queries and graph algorithms | `hivemind/git_queries.py`, `hivemind/git_graph.py` |
| Demo video | Record the two-session flow above |
| Live deployment or local setup | `compose.yaml`, `Dockerfile`, and `README.md` |
| Track | Select the hackathon track in the submission form |

## Video script

Show, in order:

1. HiveMind project and **Connect agent** screen.
2. A fresh Git repository being connected.
3. The writer session saving a source-linked finding.
4. A fresh OpenCode process recalling that finding.
5. The graph/provenance explanation and `status` output.

## Honest scope

The demo proves Git-aware memory handoff, provenance, checkpoint/no-change
handling, and native OpenCode integration. Do not claim that the full usefulness
comparison or real-human usability study has been completed.
