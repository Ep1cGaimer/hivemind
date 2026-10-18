"""Run focused checks and require the target document to actually be linted."""

from pathlib import Path
import subprocess

support = Path(__file__).resolve().parent
subprocess.run([
    "docker", "exec", "otel-site-trial", "npm", "exec", "--no", "--", "prettier",
    "--check", "content/en/docs/contributing/development.md",
], check=True)
subprocess.run([
    "docker", "exec", "-i", "otel-site-trial", "node", "--input-type=module", "-",
], input=(support / "check-doc.mjs").read_text(encoding="utf-8"), text=True, check=True)
