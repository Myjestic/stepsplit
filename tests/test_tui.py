"""Smoke test that drives the curses browser through a pseudo terminal."""

from __future__ import annotations

import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stepsplit import i18n as i18n_mod, scan  # noqa: E402
from tests.fixtures import write_assembly  # noqa: E402

TEST_LANGUAGE = "en"

ROOT = Path(__file__).resolve().parents[1]


def drive(command: list[str], keys: list[bytes], settle: float = 0.4) -> str:
    """Run ``command`` on a pty, send ``keys`` and return everything printed."""
    try:
        primary, secondary = pty.openpty()
    except OSError as error:
        raise unittest.SkipTest(f"PTY not available: {error}") from error
    os.set_blocking(primary, False)
    environment = {**os.environ, "TERM": "xterm", "LINES": "40", "COLUMNS": "120"}
    process = subprocess.Popen(
        command,
        stdin=secondary,
        stdout=secondary,
        stderr=secondary,
        env=environment,
        cwd=ROOT,
    )
    os.close(secondary)
    output = bytearray()

    def pump(duration: float) -> None:
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            ready, _, _ = select.select([primary], [], [], 0.05)
            if ready:
                try:
                    output.extend(os.read(primary, 65536))
                except OSError:
                    return

    try:
        pump(settle)
        for key in keys:
            os.write(primary, key)
            pump(settle)
        process.wait(timeout=10)
    finally:
        pump(0.3)
        if process.poll() is None:
            process.kill()
        os.close(primary)
    return output.decode("utf-8", "replace")


class BrowserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp(prefix="stepsplit-tui-"))
        self.source = write_assembly(self.directory / "assembly.stp")
        self.work_dir = self.directory / "index"
        self.output_dir = self.directory / "out"
        scan.build_index(self.source, self.work_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def command(self) -> list[str]:
        return [
            sys.executable,
            str(ROOT / "stepsplit.py"),
            "browse",
            str(self.source),
            "--work-dir",
            str(self.work_dir),
            "--output-dir",
            str(self.output_dir),
            "--language",
            TEST_LANGUAGE,
        ]

    def test_tree_renders_and_expands(self) -> None:
        # down to ROOT_ASM, expand, down to SUB_ASM, expand, then quit.
        screen = drive(self.command(), [b"j", b"l", b"j", b"l", b"q"])
        self.assertIn("ROOT_ASM", screen)
        self.assertIn("SUB_ASM", screen)
        self.assertIn("LEAF_PART", screen)

    def test_arrow_keys_navigate(self) -> None:
        # xterm reports cursor keys in application mode once keypad is on.
        screen = drive(self.command(), [b"\x1bOB", b"\x1bOC", b"q"])
        self.assertIn("SUB_ASM", screen)

    def test_expand_all_and_search(self) -> None:
        screen = drive(self.command(), [b"j", b"a", b"/", b"LEAF\n", b"q"], settle=0.5)
        self.assertIn("LEAF_PART", screen)
        self.assertIn("match 1/1", screen)

    def test_marking_and_exporting(self) -> None:
        # down to ROOT_ASM, expand, down to SUB_ASM, mark it, export, quit.
        screen = drive(
            self.command(),
            [b"j", b"l", b"j", b" ", b"e", b"\n", b"q"],
            settle=0.6,
        )
        marked = i18n_mod.I18n(TEST_LANGUAGE).t("tree_status_mark", n=1)
        self.assertIn(marked, screen)
        exported = list(self.output_dir.rglob("SUB_ASM*.step"))
        self.assertEqual(len(exported), 1, screen)
        text = exported[0].read_text(encoding="latin-1")
        self.assertIn("'LEAF_PART'", text)
        self.assertNotIn("'OTHER_PART'", text)


if __name__ == "__main__":
    unittest.main()
