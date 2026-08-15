"""Tests for settings persistence."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stepsplit import settings as settings_mod  # noqa: E402


class SettingsTest(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            with mock.patch.object(settings_mod, "settings_path", return_value=path):
                original = settings_mod.Settings(
                    setup_complete=True,
                    language="en",
                    export_mode="custom",
                    export_dir="/tmp/out",
                    work_mode="beside_source",
                    color=False,
                )
                saved = settings_mod.save_settings(original)
                self.assertEqual(saved, path)
                loaded = settings_mod.load_settings()
                self.assertTrue(loaded.setup_complete)
                self.assertEqual(loaded.language, "en")
                self.assertEqual(loaded.export_mode, "custom")
                self.assertEqual(loaded.export_dir, "/tmp/out")
                self.assertFalse(loaded.color)

    def test_resolve_export_beside_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "part.stp"
            source.write_text("x", encoding="utf-8")
            conf = settings_mod.Settings(export_mode="beside_source")
            self.assertEqual(
                settings_mod.resolve_export_dir(conf, source),
                source.parent / "export",
            )

    def test_unknown_fields_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"language": "de", "future": 1}), encoding="utf-8")
            with mock.patch.object(settings_mod, "settings_path", return_value=path):
                loaded = settings_mod.load_settings()
                self.assertEqual(loaded.language, "de")

    def test_list_cache_entries_reads_meta_and_size(self) -> None:
        from stepsplit import storage

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = root / "truck-1000"
            entry.mkdir()
            connection = storage.connect(entry, create=True)
            storage.write_meta(
                connection,
                {
                    "source": "/data/truck.stp",
                    "index_build_id": "20260815-113000",
                    "scan_state": "complete",
                },
            )
            connection.commit()
            connection.close()
            (entry / "blob.bin").write_bytes(b"1234567890")
            listed = settings_mod.list_cache_entries(root)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].label, "truck.stp")
            self.assertEqual(listed[0].created_label, "2026-08-15 11:30:00")
            self.assertGreaterEqual(listed[0].size_bytes, 10)
            self.assertEqual(settings_mod.cache_total_size(root), listed[0].size_bytes)


if __name__ == "__main__":
    unittest.main()
