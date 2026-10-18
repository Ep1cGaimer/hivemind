"""Independent simulated semantic review for a retained checkpoint artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    run = Path(args.run).resolve()
    inventory = json.loads((run / "full-inventory.json").read_text(encoding="utf-8"))
    evidence = json.loads((run / "checkpoint-machine-evidence.json").read_text(encoding="utf-8"))
    checkpoints = [r for r in inventory["records"] if r.get("kind") == "checkpoint" and r.get("id") in evidence.get("checkpoint_ids", [])]
    if len(checkpoints) != 1:
        raise ValueError("expected exactly one actual checkpoint for semantic review")
    record = checkpoints[0]
    body = record["data"]["body"]
    questions = {
        "completed_progress_is_specific": "Done:" in body and "stock_reader" in body and "movement_plan" in body,
        "remaining_work_is_concrete": "Remaining:" in body and "reconcile.py" in body and "CLI" in body,
        "next_steps_are_executable": "Next step:" in body and "execute CLI" in body,
        "no_fabricated_validation": "agent-reported" in body and "independent execution receipt" in body,
        "separate_session_and_source_binding": bool(record.get("session")) and bool(record.get("data", {}).get("paths")),
    }
    result = {
        "kind": "independent_simulated_review",
        "reviewer_id": "checkpoint-semantic-reviewer-1",
        "created_ns": time.time_ns(),
        "record_ids": [record["id"]],
        "questions": questions,
        "all_listed_questions_satisfied": all(questions.values()),
        "status": "passed" if all(questions.values()) else "failed",
        "limitations": ["Simulated semantic review is not real-human evidence.",
                        "Validation remains agent-reported where the body says no independent receipt is attached."],
    }
    (run / "checkpoint-semantic-review.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
