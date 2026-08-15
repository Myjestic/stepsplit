#!/usr/bin/env python3
"""Split large STEP assemblies into separate files without loading them into CAD.

Without arguments, opens the interactive menu:

    python3 stepsplit.py

Pick a STEP file, build the index (with progress), browse the structure tree,
mark nodes, and export selected subtrees. The source file is read-only.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Defaults for CLI subcommands. The menu uses settings (last file) or prompts you.
# No sample STEP is shipped in this repository.
DEFAULT_SOURCE = HERE / "assembly.stp"
DEFAULT_OUTPUT_DIR = HERE / "export"
DEFAULT_WORK_DIR: Path | None = None  # None → ~/.cache/stepsplit/...

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


if __name__ == "__main__":
    from stepsplit.deps import ensure_curses, needs_curses  # noqa: E402

    argv = sys.argv[1:]
    if needs_curses(argv):
        ensure_curses(prompt=True)

    from stepsplit.cli import default_work_dir, main  # noqa: E402

    work = DEFAULT_WORK_DIR
    if work is None and DEFAULT_SOURCE.exists():
        work = default_work_dir(DEFAULT_SOURCE)
    menu_mode = not argv or argv[0] == "menu"
    if (
        work is not None
        and not menu_mode
        and "--work-dir" not in argv
        and argv[0] not in {"-h", "--help"}
    ):
        argv = [*argv, "--work-dir", str(work)]
    raise SystemExit(
        main(
            argv,
            default_source=DEFAULT_SOURCE,
            default_output_dir=DEFAULT_OUTPUT_DIR,
            default_work_dir=None if menu_mode else work,
        )
    )
