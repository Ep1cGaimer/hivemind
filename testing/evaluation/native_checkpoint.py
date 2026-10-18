"""Real OpenCode/Zen interrupted-writer checkpoint acceptance run.

The evaluator-owned boundary observer selects an actual completed native tool
boundary and interrupts the writer without supplying its private assessment to
the model. HiveMind then owns the normal bounded capture lifecycle. Every run is
retained, including invalid or failed checkpoint premises.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE / "independent_fixtures"))
sys.path.insert(0, str(ROOT / "testing" / "git_memory"))

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime
from hivemind.bridge import LocalBridge, connect, git
from hivemind.opencode_runner import OpenCodeHost
from opencode_probe import environment
from native_evaluation import inventory
import checkpoint_probe
import checkpoint_v2


MODEL = os.environ.get("HIVEMIND_OPENCODE_MODEL", "opencode/deepseek-v4.1-flash-free")


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def manifest():
    return {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "hivemind").rglob("*")
        if p.suffix in {".py", ".mjs"} and p.is_file()
    }


def configure(repo: Path) -> None:
    with (repo / ".git/info/exclude").open("a", encoding="utf-8") as excluded:
        excluded.write("\n.opencode/\nopencode.json\n")
    provider = MODEL.split("/", 1)[0]
    permissions = [
        {"action": "*", "resource": "*", "effect": "deny"},
        {"action": "read", "resource": "*", "effect": "allow"},
        {"action": "edit", "resource": "*", "effect": "allow"},
        {"action": "hivemind", "resource": "*", "effect": "allow"},
    ]
    for action in ("read", "edit"):
        for resource in (".git/**", ".opencode/**", "opencode.json"):
            permissions.append({"action": action, "resource": resource, "effect": "deny"})
    save(repo / "opencode.json", {
        "$schema": "https://opencode.ai/config.json",
        "model": MODEL,
        "share": "disabled",
        "update": "disable",
        "permissions": permissions,
        "policies": [
            {"action": "provider.use", "resource": "*", "effect": "deny"},
            {"action": "provider.use", "resource": provider, "effect": "allow"},
        ],
    })


def run_native(run: Path, repo: Path, bridge: LocalBridge) -> dict:
    output = run / "writer"
    output.mkdir()
    env = environment(run / "client")
    env.pop("HIVEMIND_AGENT_TOKEN", None)
    prompt = checkpoint_v2.WRITER_PROMPT
    result = {
        "prompt": prompt,
        "model": MODEL,
        "status": "failed",
        "session_ids": [],
        "interrupted_foreground": False,
    }
    host = OpenCodeHost(bridge, env=env, model=MODEL)
    started = time.perf_counter()
    try:
        with host:
            with (output / "native.jsonl").open("w", encoding="utf-8") as stdout, \
                    (output / "native.stderr").open("w", encoding="utf-8") as stderr:
                process = subprocess.run(
                    [host.program, "run", "--server", host.address, "--format", "json",
                     "--model", MODEL, prompt],
                    cwd=repo, env=host.env, stdout=stdout, stderr=stderr, timeout=240,
                )
            result["returncode"] = process.returncode
            result["interrupted_foreground"] = process.returncode != 0
            events = [
                json.loads(line) for line in (output / "native.jsonl").read_text(encoding="utf-8").splitlines()
                if line
            ]
            result["session_ids"] = sorted({e["sessionID"] for e in events if e.get("sessionID")})
            host.drain()
            result["status"] = "passed"
            result["capture_status"] = {
                session: bridge.get("capture_status:" + session)
                for session in result["session_ids"]
            }
            result["native_lifecycle"] = {
                session: bridge.get("opencode:" + session)
                for session in result["session_ids"]
            }
    except Exception as error:
        result["error"] = str(error)
    finally:
        result["seconds"] = time.perf_counter() - started
        if host.manifest.is_file():
            result["host"] = json.loads(host.manifest.read_text(encoding="utf-8"))
        save(output / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    run = Path(args.output).resolve() if args.output else ROOT / ".local/evaluation" / str(time.time_ns())
    run.parent.mkdir(parents=True, exist_ok=True)
    if run.exists():
        raise ValueError("Use a fresh destination; every checkpoint attempt is retained")
    before = manifest()
    declaration = {
        "mode": "real OpenCode/Zen interrupted-writer checkpoint run",
        "case": checkpoint_v2.CASE,
        "fixture_version": checkpoint_v2.VERSION,
        "model": MODEL,
        "writer_prompt": checkpoint_v2.WRITER_PROMPT,
        "boundary_rule": checkpoint_v2.STOP_RULE,
        "private_evaluator": "checkpoint_probe.py/mjs; no actor-visible answers or memory writes",
        "capture_pass_limit_seconds": 60,
        "capture_extra_pass_limit": 1,
        "implementation_manifest": before,
    }
    result = {"declaration": declaration, "status": "failed"}
    server = None
    thread = None
    prior_token = os.environ.get("HIVEMIND_AGENT_TOKEN")
    try:
        checkpoint_v2.prepare(SimpleNamespace(dest=str(run)))
        checkpoint_probe.declare(run)
        checkpoint_probe.install(run)
        save(run / "declaration.json", declaration)
        repo = run / "repo"
        configure(repo)

        password = secrets.token_hex(20)
        runtime = HiveMindRuntime({
            **os.environ,
            "HIVEMIND_BACKEND": "falkordb",
            "FALKORDB_HOST": "127.0.0.1",
            "FALKORDB_PORT": "6380",
            "FALKORDB_GRAPH": "hivemind_checkpoint_" + run.name.replace("-", "_"),
            "HIVEMIND_USERS": "checkpoint=" + password,
        })
        owner = runtime.auth.login("checkpoint", password)[1]
        project = runtime.projects.create_project(owner, "Checkpoint " + run.name)["project"]["id"]
        token, _ = runtime.auth.create_agent_token(owner, "checkpoint fixture", project)
        server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["HIVEMIND_AGENT_TOKEN"] = token
        connect(SimpleNamespace(
            repo=str(repo), url="http://127.0.0.1:" + str(server.server_port),
            project=project, remote="fixture.invalid/checkpoint-" + run.name,
            repository_id=None, branch_id=None, client="opencode",
        ))
        bridge = LocalBridge(repo)
        result["project_id"] = project
        result["repo_id"] = bridge.config["repo_id"]
        result["writer"] = run_native(run, repo, bridge)
        result["native_inventory"] = inventory(runtime, project, bridge.config["repo_id"])
        save(run / "full-inventory.json", result["native_inventory"])
        evidence = checkpoint_probe.verify(run, str(run / "full-inventory.json"))
        save(run / "checkpoint-machine-evidence.json", evidence)
        result["checkpoint_machine_evidence"] = evidence
        result["implementation_unchanged"] = before == manifest()
        checks = result["checkpoint_machine_evidence"].get("checks", {})
        result["status"] = "passed" if (
            result["writer"].get("status") == "passed"
            and result["checkpoint_machine_evidence"].get("status") == "mechanically_established_semantic_review_pending"
            and all(checks.values())
            and result["implementation_unchanged"]
        ) else "failed"
    except Exception as error:
        result["error"] = str(error)
        result["implementation_unchanged"] = before == manifest()
    finally:
        if prior_token is None:
            os.environ.pop("HIVEMIND_AGENT_TOKEN", None)
        else:
            os.environ["HIVEMIND_AGENT_TOKEN"] = prior_token
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=3)
        result["artifact_directory"] = str(run)
        save(run / "result.json", result)
        print(json.dumps({
            "status": result["status"],
            "error": result.get("error"),
            "artifact_directory": str(run),
        }))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
