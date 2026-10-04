"""Allow ``python -m stepsplit`` and the ``stepsplit`` console script."""

from __future__ import annotations

import sys


def main() -> None:
    from .cli import main as cli_main

    raise SystemExit(cli_main())


if __name__ == "__main__":
    main()
