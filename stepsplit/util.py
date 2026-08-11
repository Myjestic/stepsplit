"""Byte-based progress with throughput and estimated time remaining.

Progress is always written, including when output is redirected to a file.
Updates are rate-limited so a multi-GB scan stays readable without looking stuck.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Callable

_INVALID_FILENAME = re.compile(r"[^A-Za-z0-9._+-]+")
STEP_SUFFIXES = {".stp", ".step"}

ProgressCallback = Callable[[dict[str, object]], None]


def is_step_file(path: Path) -> bool:
    """True when ``path`` looks like a STEP clear-text file by suffix."""
    return path.suffix.lower() in STEP_SUFFIXES



def log(message: str = "") -> None:
    print(message, file=sys.stderr, flush=True)


def format_bytes(value: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:,.1f} {unit}"
        value /= 1024
    return f"{value:,.1f} TiB"


def format_duration(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


class Progress:
    """Show scan/export progress.

    Call :meth:`update` as often as you like (even every record). Rendering is
    throttled to about twice per second. When stderr is not a TTY — for example
    under ``tail -f`` — each update is a full line so the log keeps moving.

    Pass ``on_update`` to drive a UI (e.g. curses) instead of, or in addition to,
    the console. With only ``on_update`` set, console output is suppressed.
    """

    def __init__(
        self,
        label: str,
        total: int,
        start: int = 0,
        enabled: bool = True,
        interval: float = 0.5,
        on_update: ProgressCallback | None = None,
        console: bool | None = None,
    ) -> None:
        self.label = label
        self.total = max(total, 1)
        self.start_position = start
        self.enabled = enabled
        self.interval = interval
        self.on_update = on_update
        self.console = console if console is not None else on_update is None
        self.started = time.monotonic()
        self._last_render = 0.0
        self._last_position = start
        self.tty = sys.stderr.isatty()

    def update(self, position: int, detail: str = "", force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        # Always render when the byte position moved and enough time passed, or
        # when the caller forces a refresh. Never wait for a counter milestone.
        if not force and now - self._last_render < self.interval:
            return
        self._last_render = now
        self._last_position = position
        elapsed = max(now - self.started, 1e-6)
        done = max(position - self.start_position, 0)
        rate = done / elapsed
        remaining = (self.total - position) / rate if rate > 0 else 0
        percent = min(max(position, 0) / self.total * 100, 100)
        info: dict[str, object] = {
            "label": self.label,
            "percent": percent,
            "position": position,
            "total": self.total,
            "rate": rate,
            "elapsed": elapsed,
            "eta": remaining,
            "detail": detail,
        }
        if self.on_update is not None:
            self.on_update(info)
        if not self.console:
            return
        line = (
            f"{self.label}: {percent:5.1f}%  "
            f"{format_bytes(position)}/{format_bytes(self.total)}  "
            f"{format_bytes(rate)}/s  "
            f"elapsed {format_duration(elapsed)}  "
            f"ETA {format_duration(remaining)}"
        )
        if detail:
            line += f"  |  {detail}"
        if self.tty:
            print(f"\r\x1b[2K{line}", end="", file=sys.stderr, flush=True)
        else:
            print(line, file=sys.stderr, flush=True)

    def finish(self, detail: str = "") -> None:
        self.update(self.total, detail, force=True)
        if self.enabled and self.console and self.tty:
            print("", file=sys.stderr, flush=True)


def safe_filename(name: str, fallback: str = "product") -> str:
    cleaned = _INVALID_FILENAME.sub("_", name).strip("._")
    return cleaned[:120] or fallback


def open_readonly(path: Path):
    """Open the source strictly for reading; the source is never modified."""
    return os.fdopen(os.open(path, os.O_RDONLY), "rb")


def guard_output_path(source: Path, output: Path, overwrite: bool) -> None:
    source = source.resolve()
    resolved = output.resolve()
    if resolved == source:
        raise SystemExit("Refusing to write onto the source STEP file.")
    if resolved.exists() and not overwrite:
        raise SystemExit(f"{resolved} already exists. Pass --overwrite to replace it.")
