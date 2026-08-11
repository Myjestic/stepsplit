"""End-to-end tests: index, resume, validate, export and re-validate."""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stepsplit import export, model, records, scan, storage, validate  # noqa: E402
from tests.fixtures import write_assembly  # noqa: E402


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.directory = Path(tempfile.mkdtemp(prefix="stepsplit-test-"))
        cls.source = write_assembly(cls.directory / "assembly.stp")
        cls.work_dir = cls.directory / "index"
        scan.build_index(cls.source, cls.work_dir)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.directory, ignore_errors=True)

    def connection(self):
        return model.open_structure(self.source, self.work_dir)

    def test_structure_counts(self) -> None:
        with self.connection() as connection:
            counts = model.counts(connection)
        self.assertEqual(counts["products"], 4)
        self.assertEqual(counts["product_definitions"], 4)
        self.assertEqual(counts["usages"], 3)

    def test_usage_direction(self) -> None:
        with self.connection() as connection:
            rows = dict(
                (usage, (parent, child))
                for usage, parent, child in connection.execute(
                    "SELECT usage_id,parent_pd,child_pd FROM usages"
                )
            )
        self.assertEqual(rows[50], (12, 22))
        self.assertEqual(rows[51], (22, 32))
        self.assertEqual(rows[52], (12, 42))

    def test_tree_shape(self) -> None:
        with self.connection() as connection:
            roots = model.root_pds(connection)
            self.assertEqual(roots, [12])
            lines = [
                (depth, node.name)
                for depth, node in model.iter_tree(connection, 12, max_depth=None)
            ]
        self.assertEqual(
            lines,
            [
                (0, "ROOT_ASM"),
                (1, "SUB_ASM"),
                (2, "LEAF_PART"),
                (3, "LEAF_PART"),
                (1, "OTHER_PART"),
                (2, "OTHER_PART"),
            ],
        )

    def test_validation_passes(self) -> None:
        with self.connection() as connection:
            report = validate.validate_structure(connection)
        self.assertTrue(report.ok, report.render())

    def test_selector_forms(self) -> None:
        with self.connection() as connection:
            by_name = model.resolve_selector(connection, "SUB_ASM")
            by_pd = model.resolve_selector(connection, "pd:22")
            by_product = model.resolve_selector(connection, "#20")
        self.assertEqual([node.pd_id for node in by_name], [22])
        self.assertEqual([node.pd_id for node in by_pd], [22])
        self.assertEqual([node.pd_id for node in by_product], [22])

    def _export(self, selector: str, name: str, **kwargs) -> Path:
        output = self.directory / name
        with self.connection() as connection:
            node = model.resolve_selector(connection, selector)[0]
            export.export_node(
                self.source,
                self.work_dir,
                connection,
                node,
                output,
                overwrite=True,
                **kwargs,
            )
        return output

    def test_export_subassembly_is_self_contained(self) -> None:
        output = self._export("SUB_ASM", "sub.step")
        report = validate.validate_step_file(output)
        self.assertTrue(report.ok, report.render())

        text = output.read_text(encoding="latin-1")
        self.assertIn("'SUB_ASM'", text)
        self.assertIn("'LEAF_PART'", text)
        # The parent and its sibling must not leak into the sub-assembly.
        self.assertNotIn("'ROOT_ASM'", text)
        self.assertNotIn("'OTHER_PART'", text)
        self.assertNotIn("'other solid'", text)
        # The solid is only reachable through a backward reference.
        self.assertIn("'leaf solid'", text)
        # The category aggregate was trimmed to the exported products.
        self.assertIn("PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#20,#30))", text)

    def test_export_keeps_original_ids_and_text(self) -> None:
        output = self._export("LEAF_PART", "leaf.step")
        text = output.read_text(encoding="latin-1")
        self.assertIn("#92=MANIFOLD_SOLID_BREP('leaf solid',#91);", text)
        self.assertIn("#30=PRODUCT('LEAF_PART','LEAF_PART','',(#3));", text)

    def test_export_of_the_root_keeps_every_product(self) -> None:
        output = self._export("ROOT_ASM", "root.step")
        text = output.read_text(encoding="latin-1")
        for product in ("ROOT_ASM", "SUB_ASM", "LEAF_PART", "OTHER_PART"):
            self.assertIn(f"'{product}'", text)
        report = validate.validate_step_file(output)
        self.assertTrue(report.ok, report.render())

    def test_pass_based_closure_matches_random_access(self) -> None:
        random_access = self._export("SUB_ASM", "sub_random.step", closure_mode="random")
        sequential = self._export("SUB_ASM", "sub_passes.step", closure_mode="passes")
        self.assertEqual(
            _entity_ids(random_access),
            _entity_ids(sequential),
            "closure modes must select the same entities",
        )

    def test_dry_run_writes_nothing(self) -> None:
        output = self.directory / "dry.step"
        with self.connection() as connection:
            node = model.resolve_selector(connection, "SUB_ASM")[0]
            result = export.export_node(
                self.source, self.work_dir, connection, node, output, dry_run=True
            )
        self.assertFalse(output.exists())
        self.assertGreater(result.bytes_written, 0)

    def test_source_is_never_modified(self) -> None:
        before = self.source.read_bytes()
        self._export("LEAF_PART", "leaf_again.step")
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_reference_is_reported(self) -> None:
        broken = self.directory / "broken.step"
        broken.write_text(
            "ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n#1=A(#404);\nENDSEC;\n"
            "END-ISO-10303-21;\n",
            encoding="latin-1",
        )
        report = validate.validate_step_file(broken)
        self.assertFalse(report.ok)
        self.assertIn("#404", report.errors[0])


def _entity_ids(path: Path) -> set[int]:
    with path.open("rb") as handle:
        return {
            entity
            for _, record in records.iter_records(handle)
            if (entity := records.record_id(record)) is not None
        }


class ResumeTest(unittest.TestCase):
    """An aborted scan must continue where it stopped and reach the same state."""

    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp(prefix="stepsplit-resume-"))
        self.source = write_assembly(self.directory / "assembly.stp")

    def tearDown(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_interrupted_scan_resumes(self) -> None:
        reference_dir = self.directory / "reference"
        scan.build_index(self.source, reference_dir)
        with model.open_structure(self.source, reference_dir) as connection:
            expected = model.counts(connection)
            expected_meta = storage.read_meta(connection)

        work_dir = self.directory / "interrupted"
        original = records.iter_records
        stop_after = 20

        def failing_iter(handle, start=0, chunk_size=records.DEFAULT_CHUNK_SIZE):
            for index, item in enumerate(original(handle, start, chunk_size)):
                if index >= stop_after:
                    raise KeyboardInterrupt
                yield item

        scan.CHECKPOINT_BYTES = 64
        records.iter_records = failing_iter
        try:
            with self.assertRaises(KeyboardInterrupt):
                scan.build_index(self.source, work_dir)
        finally:
            records.iter_records = original
            scan.CHECKPOINT_BYTES = 256 << 20

        with storage.connect(work_dir) as connection:
            partial = storage.read_meta(connection)
        self.assertEqual(partial["scan_state"], "running")
        self.assertGreater(int(partial["scan_offset"]), 0)
        self.assertLess(int(partial["scan_offset"]), self.source.stat().st_size)

        scan.build_index(self.source, work_dir)
        with model.open_structure(self.source, work_dir) as connection:
            self.assertEqual(model.counts(connection), expected)
            resumed_meta = storage.read_meta(connection)
        self.assertEqual(resumed_meta["scan_entities"], expected_meta["scan_entities"])
        self.assertEqual(resumed_meta["scan_max_id"], expected_meta["scan_max_id"])

    def test_changed_source_is_rejected(self) -> None:
        work_dir = self.directory / "index"
        scan.build_index(self.source, work_dir)
        with self.source.open("a", encoding="latin-1") as handle:
            handle.write("\n")
        with self.assertRaises(SystemExit):
            model.open_structure(self.source, work_dir)


if __name__ == "__main__":
    unittest.main()
