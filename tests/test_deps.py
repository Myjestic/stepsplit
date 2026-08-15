"""Tests for runtime dependency helpers."""

from __future__ import annotations

import sys
import unittest
from unittest import mock

from stepsplit import deps


class DepsTest(unittest.TestCase):
    def test_needs_curses_for_interactive_commands(self) -> None:
        self.assertTrue(deps.needs_curses([]))
        self.assertTrue(deps.needs_curses(["menu"]))
        self.assertTrue(deps.needs_curses(["browse", "file.stp"]))
        self.assertFalse(deps.needs_curses(["index", "file.stp"]))
        self.assertFalse(deps.needs_curses(["--help"]))
        self.assertFalse(deps.needs_curses(["export", "file.stp", "--select", "A"]))

    def test_required_package_on_windows(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(deps.required_curses_package(), "windows-curses")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertIsNone(deps.required_curses_package())

    def test_ensure_curses_is_noop_when_available(self) -> None:
        with mock.patch.object(deps, "curses_available", return_value=True):
            deps.ensure_curses(prompt=False)

    def test_ensure_curses_exits_with_install_hint_on_windows(self) -> None:
        with (
            mock.patch.object(deps, "curses_available", return_value=False),
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(deps, "_prompt_yes", return_value=False),
            mock.patch("builtins.print"),
            self.assertRaises(SystemExit) as raised,
        ):
            deps.ensure_curses(prompt=True)
        message = str(raised.exception)
        self.assertIn("windows-curses", message)
        self.assertIn("pip install", message)

    def test_ensure_curses_installs_when_accepted(self) -> None:
        available = iter([False, True])

        def fake_available() -> bool:
            return next(available)

        with (
            mock.patch.object(deps, "curses_available", side_effect=fake_available),
            mock.patch.object(sys, "platform", "win32"),
            mock.patch.object(deps, "_prompt_yes", return_value=True),
            mock.patch.object(deps, "install_package") as install,
            mock.patch.object(deps, "_purge_curses_modules"),
            mock.patch("builtins.print"),
        ):
            deps.ensure_curses(prompt=True)
        install.assert_called_once_with("windows-curses")


if __name__ == "__main__":
    unittest.main()
