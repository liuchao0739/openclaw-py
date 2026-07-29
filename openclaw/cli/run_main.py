from __future__ import annotations

import sys
from typing import Any


def run_main(argv: list[str] | None = None) -> int:
    from openclaw.cli.main import main

    try:
        main()
        return 0
    except SystemExit as e:
        return e.code or 0
    except KeyboardInterrupt:
        print("
Interrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
