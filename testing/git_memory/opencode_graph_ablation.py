"""Real OpenCode/Zen decision comparison with a live graph relationship ablation."""
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

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from native_evaluation import configure, run_model

MODEL = os.environ.get("HIVEMIND_OPENCODE_MODEL", "opencode/deepseek-v4.1-flash-free")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def implementation():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / "hivemind").rglob("*") if p.suffix in {".py", ".mjs"}}


def text_from(run):
    path = Path(run["artifact_directory"]) / "native.jsonl"
    if not path.is_file():
        return ""
    return "\n".join(json.loads(line).get("part", {}).get("text", "")
                     for line in path.read_text(encoding="utf-8").splitlines()
                     if line and json.loads(line).get("type") == "text")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    output = Path(args.output).resolve() if args.output else ROOT / ".local/git-memory/graph-ablation" / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    before = implementation()
    password = secrets.token_hex(20)
    runtime = HiveMindRuntime({**os.environ, "HIVEMIND_BACKEND": "falkordb", "FALKORDB_HOST": "127.0.0.1",
        "FALKORDB_PORT": "6380", "FALKORDB_GRAPH": "hivemind_graph_ablation_" + output.name,
        "HIVEMIND_USERS": "ablation=" + password})
    owner = runtime.auth.login("ablation", password)[1]
    project = runtime.projects.create_project(owner, "Graph ablation " + output.name)["project"]["id"]
    token, _ = runtime.auth.create_agent_token(owner, "graph ablation", project)
    server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    prior = os.environ.get("HIVEMIND_AGENT_TOKEN")
    result = {"model": MODEL, "status": "failed", "implementation_manifest": before}
    try:
        repo = output / "repo"; repo.mkdir()
        git(repo, "init", "-b", "main")
        git(repo, "config", "user.email", "ablation@example.invalid")
        git(repo, "config", "user.name", "Graph ablation fixture")
        (repo / "worker.py").write_text("def process(items):\n    return list(items)\n", encoding="utf-8")
        git(repo, "add", "."); git(repo, "commit", "-m", "Graph ablation fixture")
        os.environ["HIVEMIND_AGENT_TOKEN"] = token
        connect(SimpleNamespace(repo=str(repo), url="http://127.0.0.1:" + str(server.server_port),
            project=project, remote="fixture.invalid/ablation-" + output.name,
            repository_id=None, branch_id=None, client="opencode"))
        configure(repo, output / "tool-execution.jsonl", condition="hivemind")
        bridge = LocalBridge(repo)
        finding = bridge.call("finding", {"title": "Worker batch limit after failed approach",
            "body": "A prior 70-item attempt failed because this worker accepts at most 32 items per call. Use batches 32, 32, 6 and preserve order.",
            "paths": ["worker.py"], "session": "seed"})["memory"]
        intact_recall = bridge.call("recall", {"query": "70 items worker batches"})
        prompt = ("Decide how to send a list of 70 items through worker.py. Return strict JSON with "
                  "item_count, batch_sizes, preserves_order, and source. If a trustworthy shared "
                  "finding supplies the operational constraint, use it; otherwise state the missing "
                  "constraint and plan a validation step. Do not edit files.")
        intact = run_model(repo, output / "intact", prompt, bridge=bridge)
        edges = runtime.store.edges("BRANCH_MEMORY")
        edge = next((e for e in edges if e.to_id == finding["id"]), None)
        if edge is None:
            raise ValueError("No BRANCH_MEMORY edge available for ablation")
        graph = runtime.store.connect()._graph
        graph.query("MATCH (a {id:'" + edge.from_id + "'})-[r:BRANCH_MEMORY]->(b {id:'" + edge.to_id + "'}) DELETE r")
        ablated_recall = bridge.call("recall", {"query": "70 items worker batches"})
        ablated = run_model(repo, output / "ablated", prompt, bridge=bridge)
        result.update({"finding_id": finding["id"], "intact_recall": intact_recall,
                       "ablated_recall": ablated_recall, "intact_run": intact, "ablated_run": ablated,
                       "intact_text": text_from(intact), "ablated_text": text_from(ablated),
                       "ablation": {"edge_type": edge.edge_type, "from_id": edge.from_id, "to_id": edge.to_id,
                                    "relationship_removed": True}})
        result["checks"] = {
            "relationship_removed": finding["id"] not in [m["id"] for m in ablated_recall.get("findings", [])],
            "intact_received_finding": finding["id"] in [m["id"] for m in intact_recall.get("findings", [])],
            "intact_native_succeeded": intact.get("status") == "passed",
            "ablated_native_succeeded": ablated.get("status") == "passed",
            "decision_inputs_differ": finding["id"] in intact["native_lifecycle"].get(next(iter(intact["native_lifecycle"]), ""), {}).get("delivered_memory_ids", [])
                and finding["id"] not in ablated["native_lifecycle"].get(next(iter(ablated["native_lifecycle"]), ""), {}).get("delivered_memory_ids", []),
            "implementation_unchanged": before == implementation(),
        }
        result["status"] = "passed" if all(result["checks"].values()) else "failed"
    except Exception as error:
        result["error"] = str(error)
    finally:
        if prior is None: os.environ.pop("HIVEMIND_AGENT_TOKEN", None)
        else: os.environ["HIVEMIND_AGENT_TOKEN"] = prior
        server.shutdown(); server.server_close(); thread.join(timeout=3)
        result["artifact_directory"] = str(output)
        save(output / "result.json", result)
        print(json.dumps({"status": result["status"], "artifact_directory": str(output), "error": result.get("error")}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
