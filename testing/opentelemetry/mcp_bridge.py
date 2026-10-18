"""Launch the trial's MCP server without putting its bearer token in argv."""

import json
import os
from pathlib import Path

from hivemind.mcp_server import main


if __name__ == "__main__":
    connection = json.loads(Path("/test-state/connection.json").read_text())
    os.environ["HIVEMIND_AGENT_TOKEN"] = connection["token"]
    raise SystemExit(main())
