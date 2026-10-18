"""Three-session OpenCode/Zen alternating writer/consumer handoff proof."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "testing" / "evaluation"))
sys.path.insert(0, str(ROOT / "testing" / "evaluation" / "independent_fixtures"))

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from native_evaluation import configure, inventory, run_model
from opencode_probe import environment
import suite


MODEL = os.environ.get("HIVEMIND_OPENCODE_MODEL", "opencode/deepseek-v4.1-flash-free")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def implementation():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "hivemind").rglob("*") if p.suffix in {".py", ".mjs"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    output = Path(args.output).resolve() if args.output else ROOT / ".local/git-memory/bidirectional" / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    before = implementation()
    password = secrets.token_hex(20)
    runtime = HiveMindRuntime({**os.environ, "HIVEMIND_BACKEND": "falkordb", "FALKORDB_HOST": "127.0.0.1",
        "FALKORDB_PORT": "6380", "FALKORDB_GRAPH": "hivemind_bidirectional_" + output.name,
        "HIVEMIND_USERS": "bidirectional=" + password})
    owner = runtime.auth.login("bidirectional", password)[1]
    project = runtime.projects.create_project(owner, "Bidirectional " + output.name)["project"]["id"]
    token, _ = runtime.auth.create_agent_token(owner, "bidirectional fixture", project)
    server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    prior_token = os.environ.get("HIVEMIND_AGENT_TOKEN")
    result = {"mode": "real OpenCode/Zen alternating writer-consumer", "model": MODEL,
              "roles": [], "status": "failed", "implementation_manifest": before}
    try:
        repo = output / "repo"
        repo.mkdir()
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.email", "bidirectional@example.invalid")
        git(repo, "config", "user.name", "HiveMind bidirectional fixture")
        (repo / "worker.py").write_text("MAX_BATCH = 32\n\ndef process(items):\n    if len(items) > MAX_BATCH:\n        raise ValueError('one worker accepts at most 32 items')\n    return list(items)\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "Bidirectional worker fixture")
        with (repo / ".git/info/exclude").open("a", encoding="utf-8") as excluded:
            excluded.write("\n.opencode/\nopencode.json\n")
        os.environ["HIVEMIND_AGENT_TOKEN"] = token
        connect(SimpleNamespace(repo=str(repo), url="http://127.0.0.1:" + str(server.server_port),
            project=project, remote="fixture.invalid/bidirectional-" + output.name,
            repository_id=None, branch_id=None, client="opencode"))
        configure(repo, output / "tool-execution.jsonl", condition="hivemind")
        bridge = LocalBridge(repo)
        prompts = [
            ("session-a-writer", "Review worker.py for batch-size edge cases. Explain the constraint and how a caller should handle 70 items. Leave files unchanged."),
            ("session-b-consumer-writer", "Use the prior shared finding about worker.py and 70 items. Then identify one additional concrete caller edge case that the prior finding does not cover, explain it from source, and leave files unchanged."),
            ("session-c-consumer", "Use the newest shared finding from the other session. Return a strict JSON plan with item_count, batch_sizes, preserves_order, and source, and cite the exact finding revision or source."),
        ]
        for name, prompt in prompts:
            role = run_model(repo, output / name, prompt, bridge=bridge)
            recalled = bridge.call("recall", {})
            result["roles"].append({"name": name, "run": role, "recalled_ids": [m["id"] for m in recalled.get("findings", [])]})
        result["inventory"] = inventory(runtime, project, bridge.config["repo_id"])
        sessions = [r["run"].get("session_ids", [None])[0] for r in result["roles"]]
        findings = [r for r in result["inventory"]["records"] if r.get("kind") == "finding"]
        bodies = "\n".join(json.dumps(r) for r in findings)
        result["checks"] = {
            "three_distinct_sessions": len(set(s for s in sessions if s)) == 3,
            "all_native_runs_succeeded": all(r["run"].get("status") == "passed" for r in result["roles"]),
            "writer_a_saved": bool(findings),
            "middle_session_saved_separate_learning": len(findings) >= 2,
            "no_revision_overwrite": len({r["id"] for r in findings}) == len(findings),
            "latest_consumer_received_context": bool(result["roles"][-1]["recalled_ids"]),
            "implementation_unchanged": before == implementation(),
        }
        result["status"] = "passed" if all(result["checks"].values()) else "failed"
    except Exception as error:
        result["error"] = str(error)
    finally:
        if prior_token is None:
            os.environ.pop("HIVEMIND_AGENT_TOKEN", None)
        else:
            os.environ["HIVEMIND_AGENT_TOKEN"] = prior_token
        server.shutdown(); server.server_close(); thread.join(timeout=3)
        result["artifact_directory"] = str(output)
        save(output / "result.json", result)
        print(json.dumps({"status": result["status"], "artifact_directory": str(output), "error": result.get("error")}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
