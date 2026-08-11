"""Unit tests for the record scanner and the entity parser."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stepsplit import records  # noqa: E402


def scan(text: str) -> list[bytes]:
    handle = io.BytesIO(text.encode("latin-1"))
    return [record.strip() for _, record in records.iter_records(handle, chunk_size=16)]


class ScannerTest(unittest.TestCase):
    def test_multiline_record(self) -> None:
        text = "#1=PRODUCT('A',\n'B',\n'C',(#2));\n#2=PRODUCT_CONTEXT('',#1,'x');\n"
        self.assertEqual(
            scan(text),
            [b"#1=PRODUCT('A',\n'B',\n'C',(#2));", b"#2=PRODUCT_CONTEXT('',#1,'x');"],
        )

    def test_several_records_on_one_line(self) -> None:
        self.assertEqual(scan("#1=A(1);#2=B(2);#3=C(3);"), [b"#1=A(1);", b"#2=B(2);", b"#3=C(3);"])

    def test_semicolon_inside_string(self) -> None:
        self.assertEqual(scan("#1=A('a;b');\n"), [b"#1=A('a;b');"])

    def test_doubled_apostrophe(self) -> None:
        self.assertEqual(scan("#1=A('it''s; fine');#2=B('x');"), [b"#1=A('it''s; fine');", b"#2=B('x');"])

    def test_comment_with_semicolon_and_apostrophe(self) -> None:
        text = "/* don't; stop */\n#1=A('v');\n"
        self.assertEqual(scan(text), [b"/* don't; stop */\n#1=A('v');"])

    def test_comment_between_records(self) -> None:
        text = "#1=A(1);\n/* a ; comment */\n#2=B(2);\n"
        self.assertEqual(scan(text), [b"#1=A(1);", b"/* a ; comment */\n#2=B(2);"])

    def test_offsets_point_at_the_record(self) -> None:
        payload = b"#1=A(1);\n#2=B(2);\n"
        handle = io.BytesIO(payload)
        offsets = [offset for offset, _ in records.iter_records(handle, chunk_size=4)]
        self.assertEqual(offsets, [0, 8])
        for offset in offsets:
            self.assertIsNotNone(records.record_id(payload[offset:]))

    def test_resume_from_offset(self) -> None:
        payload = b"#1=A(1);\n#2=B(2);\n#3=C(3);\n"
        handle = io.BytesIO(payload)
        found = [record.strip() for _, record in records.iter_records(handle, start=8, chunk_size=5)]
        self.assertEqual(found, [b"#2=B(2);", b"#3=C(3);"])


class ParserTest(unittest.TestCase):
    def test_record_id(self) -> None:
        self.assertEqual(records.record_id(b"\n  #42 = PRODUCT('a');"), 42)
        self.assertIsNone(records.record_id(b"ENDSEC;"))
        self.assertIsNone(records.record_id(b"#42;"))

    def test_simple_entity(self) -> None:
        parsed = records.parse_entity(b"#1=PRODUCT('a','b','c',(#3));")
        self.assertEqual(parsed, [("PRODUCT", [b"'a'", b"'b'", b"'c'", b"(#3)"])])

    def test_complex_entity(self) -> None:
        record = (
            b"#102=(REPRESENTATION_RELATIONSHIP('','',#82,#80)"
            b"REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#101)"
            b"SHAPE_REPRESENTATION_RELATIONSHIP());"
        )
        parsed = records.parse_entity(record)
        self.assertEqual(
            [name for name, _ in parsed],
            [
                "REPRESENTATION_RELATIONSHIP",
                "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION",
                "SHAPE_REPRESENTATION_RELATIONSHIP",
            ],
        )
        self.assertEqual(parsed[0][1], [b"''", b"''", b"#82", b"#80"])
        self.assertEqual(parsed[2][1], [])

    def test_type_names_inside_strings_are_ignored(self) -> None:
        record = b"#1=PROPERTY_DEFINITION('PRODUCT_DEFINITION(','',#2);"
        self.assertEqual(records.entity_types(record), ["PROPERTY_DEFINITION"])

    def test_peek_type_names(self) -> None:
        self.assertEqual(
            records.peek_type_names(b"#1=SHAPE_REPRESENTATION_RELATIONSHIP('',#2,#3);"),
            {"SHAPE_REPRESENTATION_RELATIONSHIP"},
        )
        self.assertEqual(
            records.peek_type_names(
                b"#10=(REPRESENTATION_RELATIONSHIP('','',#1,#2) "
                b"REPRESENTATION_RELATIONSHIP_WITH_TRANSFORM(#3));"
            ),
            {
                "REPRESENTATION_RELATIONSHIP",
                "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORM",
            },
        )
        self.assertEqual(
            records.peek_type_names(b"#1=PROPERTY_DEFINITION('PRODUCT_DEFINITION(','',#2);"),
            {"PROPERTY_DEFINITION"},
        )

    def test_usage_arguments_are_positional(self) -> None:
        record = (
            b"#50=NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','Next assembly relationship',\n"
            b"'SUB_ASM',#12,#22,$);"
        )
        _, arguments = records.parse_entity(record)[0]
        self.assertEqual(records.argument_ref(arguments[3]), 12)
        self.assertEqual(records.argument_ref(arguments[4]), 22)

    def test_decode_step_string(self) -> None:
        self.assertEqual(records.decode_step_string(b"'it''s'"), "it's")
        self.assertEqual(records.decode_step_string(rb"'\X2\00DC\X0\ber'"), "Über")
        self.assertEqual(records.decode_step_string(rb"'\X\e9t\X\e9'"), "été")

    def test_entity_refs_skips_the_own_id(self) -> None:
        self.assertEqual(records.entity_refs(b"#7=A(#1,#2,#2);"), [1, 2, 2])


class FilterTest(unittest.TestCase):
    def test_filters_nested_reference_list(self) -> None:
        record = b"#140=PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#10,#20,#30,#40));"
        result = records.filter_reference_lists(record, {20, 30})
        self.assertEqual(result, b"#140=PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#20,#30));")

    def test_keeps_record_when_everything_is_selected(self) -> None:
        record = b"#140=PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#10,#20));"
        self.assertIs(records.filter_reference_lists(record, {10, 20}), record)

    def test_drops_record_when_the_list_becomes_empty(self) -> None:
        record = b"#140=PRODUCT_RELATED_PRODUCT_CATEGORY('part','',(#10));"
        self.assertIsNone(records.filter_reference_lists(record, {99}))

    def test_leaves_scalar_references_untouched(self) -> None:
        record = b"#139=MDGPR('',(#137,#138),#64);"
        result = records.filter_reference_lists(record, {137, 64})
        self.assertEqual(result, b"#139=MDGPR('',(#137),#64);")

    def test_ignores_references_inside_strings(self) -> None:
        record = b"#1=A('keep #99 as text',(#5,#6));"
        self.assertEqual(
            records.filter_reference_lists(record, {5}), b"#1=A('keep #99 as text',(#5));"
        )


if __name__ == "__main__":
    unittest.main()
