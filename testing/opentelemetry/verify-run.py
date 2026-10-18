"""Verify recorded evidence from the real writer/consumer MCP trial."""

from __future__ import annotations

import json
import subprocess

from trial import REPO, STATE, request


def events(stage):
    return [json.loads(line) for line in (STATE / f"{stage}-events.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]


def calls(rows, name):
    return [row["item"] for row in rows if row.get("type") == "item.completed"
            and row.get("item", {}).get("type") == "mcp_tool_call"
            and row["item"].get("server") == "hivemind_otel"
            and row["item"].get("tool") == name
            and row["item"].get("status") == "completed" and not row["item"].get("error")]


def content(call):
    result = call["result"]
    structured = result.get("structured_content") or result.get("structuredContent")
    if structured is not None:
        return structured
    return json.loads(next(item["text"] for item in result["content"] if item["type"] == "text"))


def thread(rows):
    return next(row["thread_id"] for row in rows if row.get("type") == "thread.started")


if __name__ == "__main__":
    writer, consumer = events("writer"), events("consumer")
    for stage, rows in [("writer", writer), ("consumer", consumer)]:
        assert any(row.get("type") == "turn.completed" for row in rows), f"{stage} did not finish"
        assert not any(row.get("type") in {"turn.failed", "error"} for row in rows), f"{stage} failed"
    assert thread(writer) != thread(consumer), "The consumer must be a fresh thread"
    writer_note = next(content(call)["memory"] for call in calls(writer, "create_memory")
        if content(call).get("memory", {}).get("title") == "Writer handoff: contributor setup and validation")
    outcome = next(content(call)["memory"] for call in calls(consumer, "create_memory")
        if content(call).get("memory", {}).get("title") == "Consumer outcome: contributor setup clarification")
    returned = [memory for call in calls(consumer, "list_memories")
                for memory in content(call).get("memories", [])]
    assert any(memory["id"] == writer_note["id"] and memory["version"] == writer_note["version"]
               for memory in returned), "Consumer did not retrieve the writer's exact version"
    assert writer_note["id"] in outcome["body"], "Consumer outcome must name the actual writer memory"
    first_recall = next(index for index, row in enumerate(consumer)
                        if row.get("item", {}).get("type") == "mcp_tool_call"
                        and row["item"].get("tool") == "list_memories")
    edits = [index for index, row in enumerate(consumer)
             if row.get("item", {}).get("type") == "file_change"]
    assert edits and first_recall < min(edits), "Recall must precede editing"
    changed = subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-only"], text=True).splitlines()
    expected = "content/en/docs/contributing/development.md"
    assert changed == [expected], f"Unexpected changed files: {changed}"
    assert not subprocess.check_output(["git", "-C", str(REPO), "diff", "--cached", "--name-only"]), "Unexpected staged changes"
    untracked = subprocess.check_output(["git", "-C", str(REPO), "ls-files", "--others", "--exclude-standard"], text=True)
    assert not untracked, f"Unexpected untracked files: {untracked}"
    consumer_commands = "\n".join(row.get("item", {}).get("command", "") for row in consumer)
    for transcript_name in ["writer-events.jsonl", "writer-final.txt", "session-1-writer.txt"]:
        assert transcript_name not in consumer_commands, f"Consumer accessed writer transcript: {transcript_name}"
    checks = [row["item"] for row in consumer if row.get("type") == "item.completed"
              and row.get("item", {}).get("type") == "command_execution"
              and "check-doc.py" in row["item"].get("command", "")]
    assert any(item.get("exit_code") == 0 for item in checks), "Direct document checks did not pass"
    connection = json.loads((STATE / "connection.json").read_text())
    current = request(f"/api/projects/{connection['project_id']}/memories", token=connection["token"])["memories"]
    assert {writer_note["id"], outcome["id"]} <= {note["id"] for note in current}
    patch = subprocess.check_output(["git", "-C", str(REPO), "diff", "--", expected])
    (STATE / "consumer.patch").write_bytes(patch)
    report = {
        "ok": True,
        "writer_thread_id": thread(writer), "consumer_thread_id": thread(consumer),
        "writer_memory_id": writer_note["id"], "writer_memory_version": writer_note["version"],
        "consumer_memory_id": outcome["id"], "consumer_memory_version": outcome["version"],
        "checks": ["two completed independent threads", "writer saved through MCP",
                   "consumer retrieved exact writer version before editing",
                   "consumer recorded the writer memory ID", "only intended document changed",
                   "direct document checks passed", "both notes persisted in project HTTP API"],
        "changed_files": changed,
        "scope": "project, not Git branch",
        "automatic_capture": False,
        "graph_vs_regular_rag_advantage_measured": False,
    }
    (STATE / "run-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
