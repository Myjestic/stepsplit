"""Runtime dependency checks (especially Windows curses support)."""

from __future__ import annotations

import importlib
import subprocess
import sys


WINDOWS_CURSES = "windows-curses"


def curses_available() -> bool:
    """Return True when the curses / _curses modules can be imported."""
    try:
        importlib.import_module("curses")
        importlib.import_module("_curses")
        return True
    except ImportError:
        return False


def _purge_curses_modules() -> None:
    """Drop partial curses imports so a fresh attempt can succeed after install."""
    for name in list(sys.modules):
        if name == "curses" or name == "_curses" or name.startswith("curses."):
            del sys.modules[name]


def required_curses_package() -> str | None:
    """Package to install when curses is missing, or None if we cannot auto-fix."""
    if sys.platform == "win32":
        return WINDOWS_CURSES
    return None


def install_package(package: str) -> None:
    """Install ``package`` with the same Python that is running StepSplit."""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def _prompt_yes(question: str, *, default_yes: bool = True) -> bool:
    if not sys.stdin.isatty():
        return False
    hint = "Y/n" if default_yes else "y/N"
    try:
        answer = input(f"{question} [{hint}] ").strip().lower()
    except EOFError:
        return False
    if not answer:
        return default_yes
    return answer in {"y", "yes", "j", "ja"}


def ensure_curses(*, prompt: bool = True) -> None:
    """Make sure curses works; on Windows offer to install ``windows-curses``.

    Raises ``SystemExit`` with a clear message when curses cannot be provided.
    """
    if curses_available():
        return

    package = required_curses_package()
    if package is None:
        raise SystemExit(
            "StepSplit needs the Python curses module for the interactive menu "
            "and structure tree.\n"
            "Install a curses-capable Python build, or use the non-interactive "
            "CLI commands (index, tree, export, check)."
        )

    print(
        "StepSplit needs a terminal UI library that Python does not ship on Windows.\n"
        f"Missing module: _curses  →  install '{package}'\n"
    )
    pip_cmd = f'{sys.executable} -m pip install {package}'

    if prompt and _prompt_yes(f"Install '{package}' now with pip?"):
        try:
            print(f"\nRunning: {pip_cmd}\n")
            install_package(package)
        except (subprocess.CalledProcessError, OSError) as error:
            raise SystemExit(
                f"Could not install '{package}': {error}\n"
                f"Try manually:\n  {pip_cmd}\n"
                "If no wheel exists for your Python version, use Python 3.10-3.12."
            ) from error
        _purge_curses_modules()
        if curses_available():
            print(f"\nInstalled '{package}' successfully. Starting StepSplit…\n")
            return
        raise SystemExit(
            f"'{package}' was installed, but curses still cannot be imported.\n"
            "Restart the terminal and run StepSplit again, or use Python 3.10-3.12."
        )

    raise SystemExit(
        f"Cannot start the interactive UI without '{package}'.\n"
        f"Install it with:\n  {pip_cmd}\n"
        "Or use non-interactive commands, for example:\n"
        "  python stepsplit.py index path\\to\\assembly.stp\n"
        "  python stepsplit.py export path\\to\\assembly.stp --select PART_NAME"
    )


def needs_curses(argv: list[str]) -> bool:
    """True when this invocation will open the curses menu or browser."""
    if not argv or argv[0] in {"menu", "browse"}:
        return True
    return False
