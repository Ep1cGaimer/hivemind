"""Run real Chromium acceptance checks against the local HiveMind UI.

The browser is project-local Playwright/Chromium. The script creates an in-memory
service in-process, invokes the browser scenario, retains screenshots and machine
results under an ignored artifact directory, and shuts the service down.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from hivemind.api import HiveMindHTTPServer, HiveMindRuntime


def main() -> int:
    output = ROOT / ".local/usability/browser" / str(time.time_ns())
    output.mkdir(parents=True, exist_ok=False)
    runtime = HiveMindRuntime({**os.environ, "HIVEMIND_BACKEND": "memory"})
    server = HiveMindHTTPServer(("127.0.0.1", 0), runtime=runtime)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://127.0.0.1:" + str(server.server_port)
    try:
        child_env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH="0", PYTHONUTF8="1")
        result = subprocess.run(
            ["node", str(ROOT / "testing/usability/browser_acceptance.mjs"), url, str(output)],
            cwd=ROOT, env=child_env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        (output / "node.stdout").write_text(result.stdout, encoding="utf-8")
        (output / "node.stderr").write_text(result.stderr, encoding="utf-8")
        report_path = output / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {
            "status": "failed", "error": "Browser runner did not write report.json"
        }
        report["returncode"] = result.returncode
        report["artifact_directory"] = str(output)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"status": report.get("status"), "artifact_directory": str(output),
                          "error": report.get("error")}))
        return 0 if result.returncode == 0 and report.get("status") == "passed" else 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
