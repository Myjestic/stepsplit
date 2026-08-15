"""Validation of the indexed assembly graph and of generated STEP files."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import i18n as i18n_mod
from . import model, records, storage
from .util import Progress, format_bytes, log, open_readonly

ERROR = "error"
WARNING = "warning"
INFO = "info"

# Cycle detection needs the whole usage graph in memory; above this many edges
# the check is skipped instead of risking a multi-gigabyte dictionary.
MAX_CYCLE_CHECK_EDGES = 5_000_000


def _fmt_int(value: int) -> str:
    text = f"{value:,}"
    if i18n_mod.get_i18n().language == "de":
        return text.replace(",", ".")
    return text


@dataclass
class Report:
    findings: list[tuple[str, str]] = field(default_factory=list)

    def add(self, severity: str, message: str) -> None:
        self.findings.append((severity, message))

    @property
    def errors(self) -> list[str]:
        return [text for severity, text in self.findings if severity == ERROR]

    @property
    def warnings(self) -> list[str]:
        return [text for severity, text in self.findings if severity == WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        tr = i18n_mod.get_i18n().t
        symbols = {ERROR: tr("sev_fail"), WARNING: tr("sev_warn"), INFO: tr("sev_ok")}
        width = max(len(symbols[ERROR]), len(symbols[WARNING]), len(symbols[INFO]))
        lines = [
            f"[{symbols[severity].ljust(width)}] {text}"
            for severity, text in self.findings
        ]
        lines.append("")
        lines.append(tr("val_result_ok") if self.ok else tr("val_result_bad"))
        return "\n".join(lines)


def validate_structure(connection: sqlite3.Connection) -> Report:
    """Check that the indexed assembly relationships are complete and sane."""
    report = Report()
    stats = model.counts(connection)
    tr = i18n_mod.get_i18n().t

    if stats["products"] == 0:
        report.add(ERROR, tr("val_no_products"))
    else:
        report.add(INFO, tr("val_n_products", n=_fmt_int(stats["products"])))

    if stats["product_definitions"] == 0:
        report.add(ERROR, tr("val_no_product_definitions"))
    else:
        report.add(
            INFO,
            tr("val_n_product_definitions", n=_fmt_int(stats["product_definitions"])),
        )

    if stats["usages"] == 0:
        # Zero links usually means a single part or a flat STEP — not a parser failure.
        if stats["products"] > 1:
            report.add(WARNING, tr("val_no_usages_multi"))
        else:
            report.add(INFO, tr("val_no_usages"))
    else:
        report.add(INFO, tr("val_n_usages", n=_fmt_int(stats["usages"])))

    fallbacks = connection.execute(
        "SELECT COUNT(*) FROM usages WHERE parse_mode <> 'positional'"
    ).fetchone()[0]
    if fallbacks:
        report.add(WARNING, tr("val_fallback_usages", n=_fmt_int(fallbacks)))

    if stats["usages"] > 0:
        dangling_parents = connection.execute(
            "SELECT COUNT(*) FROM usages u WHERE NOT EXISTS "
            "(SELECT 1 FROM product_definitions pd WHERE pd.pd_id = u.parent_pd)"
        ).fetchone()[0]
        dangling_children = connection.execute(
            "SELECT COUNT(*) FROM usages u WHERE NOT EXISTS "
            "(SELECT 1 FROM product_definitions pd WHERE pd.pd_id = u.child_pd)"
        ).fetchone()[0]
        if dangling_parents or dangling_children:
            report.add(
                ERROR,
                tr(
                    "val_dangling_usages",
                    parents=_fmt_int(dangling_parents),
                    children=_fmt_int(dangling_children),
                ),
            )
        else:
            report.add(INFO, tr("val_usages_ok"))

    unnamed = connection.execute(
        """
        SELECT COUNT(*) FROM product_definitions pd
        WHERE NOT EXISTS (
            SELECT 1 FROM formations f
            JOIN products p ON p.product_id = f.product_id
            WHERE f.formation_id = pd.formation_id
        )
        """
    ).fetchone()[0]
    if unnamed:
        report.add(WARNING, tr("val_unnamed_pds", n=_fmt_int(unnamed)))
    else:
        report.add(INFO, tr("val_names_ok"))

    without_shape = connection.execute(
        """
        SELECT COUNT(*) FROM product_definitions pd
        WHERE NOT EXISTS (
            SELECT 1 FROM definition_shapes ds WHERE ds.definition_id = pd.pd_id
        )
        """
    ).fetchone()[0]
    if without_shape:
        report.add(WARNING, tr("val_without_shape", n=_fmt_int(without_shape)))
    else:
        report.add(INFO, tr("val_shapes_ok"))

    roots = model.root_pds(connection)
    if not roots:
        report.add(ERROR, tr("val_no_roots"))
    else:
        names = model.names_for_pds(connection, roots[:10])
        preview = ", ".join(f"{names[pd_id]} [#{pd_id}]" for pd_id in roots[:10])
        report.add(INFO, tr("val_roots", n=_fmt_int(len(roots)), preview=preview))

    if stats["usages"] > MAX_CYCLE_CHECK_EDGES:
        report.add(
            INFO,
            tr(
                "val_cycle_skipped",
                n=_fmt_int(stats["usages"]),
                limit=_fmt_int(MAX_CYCLE_CHECK_EDGES),
            ),
        )
    else:
        cycles = _find_cycles(connection)
        if cycles:
            preview = ", ".join(f"#{pd_id}" for pd_id in cycles[:10])
            report.add(
                WARNING,
                tr("val_cycles", n=_fmt_int(len(cycles)), preview=preview),
            )
        else:
            report.add(INFO, tr("val_acyclic"))

    ambiguous = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT p.name FROM products p
            JOIN formations f            ON f.product_id   = p.product_id
            JOIN product_definitions pd  ON pd.formation_id = f.formation_id
            GROUP BY p.name HAVING COUNT(DISTINCT pd.pd_id) > 1
        )
        """
    ).fetchone()[0]
    if ambiguous:
        report.add(WARNING, tr("val_ambiguous_names", n=_fmt_int(ambiguous)))

    return report


def _find_cycles(connection: sqlite3.Connection) -> list[int]:
    """Detect product definitions that participate in a usage cycle."""
    edges: dict[int, list[int]] = {}
    for parent, child in connection.execute("SELECT parent_pd, child_pd FROM usages"):
        edges.setdefault(parent, []).append(child)

    WHITE, GREY, BLACK = 0, 1, 2
    colour: dict[int, int] = {}
    on_cycle: set[int] = set()

    for start in list(edges):
        if colour.get(start, WHITE) != WHITE:
            continue
        stack: list[tuple[int, bool]] = [(start, False)]
        while stack:
            node, leaving = stack.pop()
            if leaving:
                colour[node] = BLACK
                continue
            if colour.get(node, WHITE) != WHITE:
                continue
            colour[node] = GREY
            stack.append((node, True))
            for child in edges.get(node, ()):
                state = colour.get(child, WHITE)
                if state == GREY:
                    on_cycle.add(child)
                elif state == WHITE:
                    stack.append((child, False))
    return sorted(on_cycle)


def sample_usages(connection: sqlite3.Connection, source: Path, work_dir: Path, limit: int = 5):
    """Return raw text of a few usage records so the parser can be reviewed."""
    rows = connection.execute(
        "SELECT usage_id, parent_pd, child_pd, usage_type, parse_mode FROM usages"
        " ORDER BY usage_id LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows or not model.has_offsets(work_dir):
        return [(row, None) for row in rows]

    samples = []
    with storage.OffsetIndex(storage.offsets_path(work_dir), readonly=True) as offsets:
        with open_readonly(source) as handle:
            for row in rows:
                offset = offsets.get(row[0])
                if offset is None:
                    samples.append((row, None))
                    continue
                handle.seek(offset)
                chunk = handle.read(4096)
                end = records.find_terminator(chunk)
                samples.append((row, chunk[: end + 1].strip() if end >= 0 else chunk))
    return samples


class _MemoryBitSet:
    """Growable in-memory bitset; 20 MB is enough for 165 million entity ids."""

    def __init__(self) -> None:
        self._bits = bytearray(1 << 16)

    def add(self, value: int) -> bool:
        index, bit = divmod(value, 8)
        if index >= len(self._bits):
            self._bits.extend(bytearray(max(index + 1 - len(self._bits), len(self._bits))))
        mask = 1 << bit
        if self._bits[index] & mask:
            return False
        self._bits[index] |= mask
        return True

    def __contains__(self, value: int) -> bool:
        index, bit = divmod(value, 8)
        return index < len(self._bits) and bool(self._bits[index] & (1 << bit))


def validate_step_file(path: Path, examples: int = 10) -> Report:
    """Verify that every ``#id`` referenced in a STEP file is also defined.

    Two sequential passes keep the memory usage at one bit per entity id
    instead of one Python integer, so even multi-gigabyte exports can be
    checked.
    """
    report = Report()
    size = path.stat().st_size
    defined = _MemoryBitSet()
    entities = 0
    duplicates = 0
    saw_data = False
    saw_end = False

    progress = Progress(f"Checking {path.name} (ids)", size)
    with open_readonly(path) as handle:
        for offset, record in records.iter_records(handle):
            stripped = record.strip().upper()
            if stripped == b"DATA;":
                saw_data = True
            elif stripped.startswith(b"END-ISO-10303-21"):
                saw_end = True
            entity_id = records.record_id(record)
            if entity_id is None:
                continue
            entities += 1
            if not defined.add(entity_id):
                duplicates += 1
            progress.update(offset)
    progress.finish(f"{entities:,} entities")

    missing = _MemoryBitSet()
    missing_count = 0
    preview: list[str] = []
    progress = Progress(f"Checking {path.name} (references)", size)
    with open_readonly(path) as handle:
        for offset, record in records.iter_records(handle):
            holder = records.record_id(record)
            if holder is None:
                continue
            for ref in records.entity_refs(record):
                if ref not in defined and missing.add(ref):
                    missing_count += 1
                    if len(preview) < examples:
                        preview.append(f"#{ref} (used by #{holder})")
            progress.update(offset)
    progress.finish(f"{missing_count:,} missing references")

    report.add(INFO, f"{entities:,} entities, {format_bytes(size)}.")
    if not saw_data:
        report.add(ERROR, "No DATA; section marker found.")
    if not saw_end:
        report.add(ERROR, "No END-ISO-10303-21; terminator found.")
    if missing_count:
        report.add(
            ERROR,
            f"{missing_count:,} references point to missing entities: " + ", ".join(preview),
        )
    else:
        report.add(INFO, "Every reference resolves inside the file.")
    if duplicates:
        report.add(ERROR, f"{duplicates:,} duplicate entity ids.")
    return report


def log_report(report: Report) -> None:
    log(report.render())
