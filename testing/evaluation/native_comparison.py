"""Execute the declared native comparison slots without replacing failures."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    "failed_approach", "build_prerequisite", "branch_constraint",
    "stale_guidance", "integration_applicability", "no_history",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--case", action="append", choices=CASES)
    parser.add_argument("--seed", type=int, default=1900)
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.repetitions < 1 or args.repetitions > 3:
        parser.error("repetitions must be between 1 and 3")
    cases = tuple(args.case or CASES)
    output = Path(args.output).resolve() if args.output else ROOT / ".local/evaluation/comparison" / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    declaration = {
        "mode": "real OpenCode/Zen repeated comparison; pilot unless all eight cases are run",
        "cases": cases,
        "conditions": ["source_only", "source_linked_notes", "hivemind"],
        "repetitions": args.repetitions,
        "planned_consumer_runs": len(cases) * args.repetitions * 3,
        "model": os.environ.get("HIVEMIND_OPENCODE_MODEL", "opencode/deepseek-v4.1-flash-free"),
        "opencode_binary": os.environ.get("HIVEMIND_OPENCODE_BIN"),
        "seed": args.seed,
        "failure_policy": "retain each external result; never retry into a replacement slot",
        "source_manifest_sha256": hashlib.sha256(
            json.dumps({p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in (ROOT / "hivemind").rglob("*") if p.suffix in {".py", ".mjs"}}, sort_keys=True).encode()
        ).hexdigest(),
    }
    (output / "declaration.json").write_text(json.dumps(declaration, indent=2), encoding="utf-8")
    slots = []
    for repetition in range(1, args.repetitions + 1):
        for index, case in enumerate(cases):
            slot = output / f"{repetition:02}-{index + 1:02}-{case}"
            command = [sys.executable, str(ROOT / "testing/evaluation/native_evaluation.py"),
                       "--case", case, "--condition", "all", "--seed", str(args.seed + repetition * 100 + index),
                       "--output", str(slot)]
            started = time.perf_counter()
            stdout_path = slot.with_suffix(".stdout")
            stderr_path = slot.with_suffix(".stderr")
            slot.parent.mkdir(parents=True, exist_ok=True)
            with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
                process = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), stdout=stdout, stderr=stderr, timeout=1200)
            result_path = slot / "result.json"
            try:
                result = json.loads(result_path.read_text(encoding="utf-8"))
            except Exception as error:
                result = {"status": "failed", "error": "missing or invalid result: " + str(error)}
            consumer_results = result.get("consumers", [])
            entry = {
                "case": case,
                "repetition": repetition,
                "returncode": process.returncode,
                "seconds": time.perf_counter() - started,
                "artifact_directory": str(slot),
                "status": result.get("status", "failed"),
                "consumer_statuses": [c.get("run", {}).get("status", "failed") for c in consumer_results],
                "outcome_statuses": [c.get("outcome", {}).get("status", "failed") for c in consumer_results],
                "result": result,
            }
            slots.append(entry)
            (output / "in-progress.json").write_text(json.dumps({"declaration": declaration, "slots": slots}, indent=2), encoding="utf-8")
            print(json.dumps({"case": case, "repetition": repetition, "status": entry["status"],
                              "artifact_directory": str(slot)}), flush=True)
    passed_consumers = sum(status == "passed" for slot in slots for status in slot["outcome_statuses"])
    completed_consumers = sum(len(slot["outcome_statuses"]) for slot in slots)
    aggregate = {
        "declaration": declaration,
        "completed_slots": len(slots),
        "completed_consumer_runs": completed_consumers,
        "passed_consumer_runs": passed_consumers,
        "slots": slots,
        "status": "passed" if completed_consumers == len(cases) * args.repetitions * 3 and passed_consumers == completed_consumers else "failed",
        "limitations": ["The six default cases omit unfinished_checkpoint and conflicting_interpretations until their native premises are integrated."] if len(cases) < 8 else [],
        "artifact_directory": str(output),
    }
    (output / "result.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(json.dumps({"status": aggregate["status"], "completed_consumer_runs": completed_consumers,
                      "passed_consumer_runs": passed_consumers, "artifact_directory": str(output)}))
    return 0 if aggregate["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
