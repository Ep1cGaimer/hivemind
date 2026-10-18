"""Launch the local HiveMind HTTP API with ``python -m hivemind``."""

import sys
from .api import main as api_main


def main():
    if len(sys.argv) > 1 and sys.argv[1] in {'connect', 'run', 'sync', 'status', 'hook', 'mcp', 'opencode-event'}:
        from .bridge import main as bridge_main
        return bridge_main()
    return api_main()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
