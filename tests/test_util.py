"""Tests for path helpers and export guards."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stepsplit.util import directory_size, guard_output_path, safe_filename  # noqa: E402


class UtilTest(unittest.TestCase):
    def test_safe_filename_strips_path_separators(self) -> None:
        self.assertNotIn("/", safe_filename("a/b\\c"))
        self.assertNotIn("\\", safe_filename("a/b\\c"))

    def test_directory_size_sums_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.bin").write_bytes(b"12345")
            nested = root / "sub"
            nested.mkdir()
            (nested / "b.bin").write_bytes(b"abcdef")
            self.assertEqual(directory_size(root), 11)
            self.assertEqual(directory_size(root / "missing"), 0)

    def test_guard_rejects_same_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "assembly.stp"
            source.write_text("ISO-10303-21;", encoding="latin-1")
            with self.assertRaises(SystemExit):
                guard_output_path(source, source, overwrite=True)

    def test_guard_rejects_hard_link_to_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "assembly.stp"
            linked = Path(tmp) / "export_alias.step"
            source.write_text("ISO-10303-21;", encoding="latin-1")
            try:
                os.link(source, linked)
            except OSError as error:
                raise unittest.SkipTest(f"hard links unavailable: {error}") from error
            with self.assertRaises(SystemExit) as raised:
                guard_output_path(source, linked, overwrite=True)
            self.assertIn("source STEP", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
