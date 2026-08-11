"""Dependency closure and STEP writing for a selected assembly subtree.

The source file is opened read-only and streamed; only entity ids ever live in
memory, and even those are kept in a file-backed bitset.
"""

from __future__ import annotations

import datetime as _datetime
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import VERSION, model, records, storage
from . import i18n as i18n_mod
from .util import (
    Progress,
    format_bytes,
    guard_output_path,
    log,
    open_readonly,
    safe_filename,
)

PhaseCallback = Callable[[str, float, str], None]
CancelCheck = Callable[[], None]


class ExportCancelled(Exception):
    """Raised when the user interrupts an export (Ctrl+C)."""


def _throttled_phase(
    on_phase: PhaseCallback | None,
    step: str,
    fraction: float,
    detail: str,
    state: dict[str, float],
    *,
    force: bool = False,
    interval: float = 0.4,
    cancel_check: CancelCheck | None = None,
) -> None:
    if cancel_check is not None:
        cancel_check()
    if on_phase is None:
        return
    import time

    now = time.monotonic()
    if not force and now - state.get("last", 0.0) < interval and fraction < 1.0:
        return
    state["last"] = now
    on_phase(step, min(max(fraction, 0.0), 1.0), detail)

READ_WINDOW = 4096

# Entities that only ever reference the selection are pulled in by a backward
# pass. "follow" adds the whole forward closure of the record, "filter" keeps
# the record but trims its aggregate reference lists to the selection.
BACKWARD_GROUPS: dict[str, dict[str, set[str]]] = {
    # Creo and Solid Edge keep the solid of a part in a separate
    # ADVANCED_BREP_SHAPE_REPRESENTATION that is only reachable backwards,
    # through a plain SHAPE_REPRESENTATION_RELATIONSHIP. The excluded types are
    # the assembly placements; following those would drag in the parent
    # assembly of the exported node.
    "geometry": {
        "follow": {
            "SHAPE_REPRESENTATION_RELATIONSHIP",
            "CONSTRUCTIVE_GEOMETRY_REPRESENTATION_RELATIONSHIP",
            "SHAPE_DEFINITION_REPRESENTATION",
        },
        "filter": set(),
        "exclude": {
            "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION",
            "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION",
        },
    },
    "styles": {
        "follow": {
            "STYLED_ITEM",
            "OVER_RIDING_STYLED_ITEM",
            "ANNOTATION_OCCURRENCE",
            "STYLED_ITEM_STYLE",
        },
        "filter": {
            "MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION",
            "PRESENTATION_LAYER_ASSIGNMENT",
        },
    },
    "categories": {
        "follow": {"APPLICATION_PROTOCOL_DEFINITION"},
        "filter": {"PRODUCT_RELATED_PRODUCT_CATEGORY", "PRODUCT_CATEGORY_RELATIONSHIP"},
    },
    "properties": {
        "follow": {
            "PROPERTY_DEFINITION",
            "PROPERTY_DEFINITION_REPRESENTATION",
            "SHAPE_ASPECT",
            "SHAPE_ASPECT_RELATIONSHIP",
            "GENERAL_PROPERTY_ASSOCIATION",
        },
        "filter": set(),
    },
}

DEFAULT_BACKWARD_GROUPS = ("geometry", "styles", "categories", "properties")

# Argument positions that decide whether a backward candidate belongs to the
# selection. Without them a shared style or context would pull in unrelated
# siblings, because those records reference the selection only incidentally.
BACKWARD_TRIGGERS: dict[str, tuple[int, ...]] = {
    "STYLED_ITEM": (2,),
    "OVER_RIDING_STYLED_ITEM": (2,),
    "ANNOTATION_OCCURRENCE": (2,),
    "PROPERTY_DEFINITION": (2,),
    "PROPERTY_DEFINITION_REPRESENTATION": (0,),
    "SHAPE_ASPECT": (2,),
    "SHAPE_ASPECT_RELATIONSHIP": (2, 3),
    "GENERAL_PROPERTY_ASSOCIATION": (3,),
    "SHAPE_DEFINITION_REPRESENTATION": (0,),
    "SHAPE_REPRESENTATION_RELATIONSHIP": (2, 3),
    "CONSTRUCTIVE_GEOMETRY_REPRESENTATION_RELATIONSHIP": (2, 3),
    "APPLICATION_PROTOCOL_DEFINITION": (3,),
}


def trigger_refs(parsed: list[tuple[str, list[bytes]]]) -> list[int] | None:
    """References that make a backward candidate relevant, ``None`` if unknown."""
    found: list[int] = []
    known = False
    for name, arguments in parsed:
        positions = BACKWARD_TRIGGERS.get(name)
        if positions is None:
            continue
        known = True
        for position in positions:
            if position < len(arguments):
                reference = records.argument_ref(arguments[position])
                if reference is not None:
                    found.append(reference)
    return found if known else None


@dataclass
class Closure:
    selected: storage.BitSet
    filtered_ids: set[int] = field(default_factory=set)
    count: int = 0
    missing_offsets: list[int] = field(default_factory=list)


@dataclass
class ExportResult:
    output: Path
    product: str
    pd_id: int
    product_definitions: int
    usages: int
    entities: int
    written: int
    dropped: int
    bytes_written: int
    dry_run: bool


def structural_seeds(
    connection: sqlite3.Connection, product_definitions: set[int], usages: set[int]
) -> set[int]:
    """Collect the structure entities that anchor a subtree in the STEP file."""
    seeds: set[int] = set(product_definitions) | set(usages)
    definitions = sorted(seeds)

    formation_ids = _lookup(
        connection,
        "SELECT pd_id, formation_id FROM product_definitions WHERE pd_id IN ({})",
        sorted(product_definitions),
    )
    seeds.update(formation_ids.values())

    product_ids = _lookup(
        connection,
        "SELECT formation_id, product_id FROM formations WHERE formation_id IN ({})",
        sorted(set(formation_ids.values())),
    )
    seeds.update(product_ids.values())

    shape_ids = _collect(
        connection,
        "SELECT pds_id FROM definition_shapes WHERE definition_id IN ({})",
        definitions,
    )
    seeds.update(shape_ids)

    for query in (
        "SELECT sdr_id, representation_id FROM shape_representations WHERE pds_id IN ({})",
        "SELECT cdsr_id, relationship_id FROM context_shapes WHERE pds_id IN ({})",
    ):
        for left, right in _rows(connection, query, sorted(shape_ids)):
            seeds.add(left)
            seeds.add(right)
    return seeds


def _rows(connection: sqlite3.Connection, query: str, keys: list[int], batch: int = 500):
    for start in range(0, len(keys), batch):
        window = keys[start : start + batch]
        placeholders = ",".join("?" * len(window))
        yield from connection.execute(query.format(placeholders), window)


def _lookup(connection: sqlite3.Connection, query: str, keys: list[int]) -> dict[int, int]:
    return {key: value for key, value in _rows(connection, query, keys)}


def _collect(connection: sqlite3.Connection, query: str, keys: list[int]) -> set[int]:
    return {row[0] for row in _rows(connection, query, keys)}


def split_refs(record: bytes) -> tuple[list[int], list[int]]:
    """Separate scalar references from those inside pure ``(#a,#b)`` aggregates."""
    aggregate: list[int] = []
    scalar: list[int] = []
    index = records.payload_start(record)
    if index < 0:
        return scalar, aggregate

    end = len(record)
    while index < end:
        char = record[index]
        if char == 0x27:  # apostrophe
            index += 1
            while index < end:
                if record[index] == 0x27:
                    if index + 1 < end and record[index + 1] == 0x27:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char == 0x28:  # (
            arguments, after = records.parse_arguments(record, index)
            refs = [records.argument_ref(argument) for argument in arguments]
            if arguments and all(ref is not None for ref in refs) and len(refs) > 0:
                aggregate.extend(ref for ref in refs if ref is not None)
                index = after
                continue
            index += 1
            continue
        if char == 0x23:  # #
            start = index + 1
            index = start
            while index < end and 0x30 <= record[index] <= 0x39:
                index += 1
            if index > start:
                scalar.append(int(record[start:index]))
            continue
        index += 1
    return scalar, aggregate


def _read_record_at(handle, offset: int) -> bytes:
    handle.seek(offset)
    chunk = handle.read(READ_WINDOW)
    end = records.find_terminator(chunk)
    while end < 0:
        more = handle.read(READ_WINDOW * 16)
        if not more:
            break
        chunk += more
        end = records.find_terminator(chunk)
    return chunk[: end + 1] if end >= 0 else chunk


def forward_closure_random(
    source: Path,
    work_dir: Path,
    closure: Closure,
    queue: storage.DiskQueue,
    label: str = "Dependency closure",
    quiet: bool = False,
    on_phase: PhaseCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> None:
    """Expand the queue using random access through the offset index."""
    offsets = storage.OffsetIndex(storage.offsets_path(work_dir), readonly=True)
    processed = 0
    tick: dict[str, float] = {}
    try:
        with open_readonly(source) as handle:
            for entity_id in queue.drain():
                offset = offsets.get(entity_id)
                processed += 1
                if offset is None:
                    closure.missing_offsets.append(entity_id)
                    continue
                record = _read_record_at(handle, offset)
                actual = records.record_id(record)
                if actual != entity_id:
                    raise SystemExit(
                        f"Offset index is inconsistent: expected #{entity_id} at byte "
                        f"{offset}, found #{actual}. Rebuild the index with --force."
                    )
                additions = [
                    ref for ref in records.entity_refs(record) if closure.selected.add(ref)
                ]
                if additions:
                    closure.count += len(additions)
                    queue.extend(additions)
                if processed % 200_000 == 0 and not quiet:
                    log(
                        f"{label}: {closure.count:,} entities selected, "
                        f"{queue.pending:,} queued"
                    )
                detail = i18n_mod.get_i18n().t(
                    "export_closure_detail",
                    selected=f"{closure.count:,}",
                    queued=f"{queue.pending:,}",
                )
                _throttled_phase(
                    on_phase,
                    "closure",
                    min(processed / max(processed + queue.pending, 1), 0.98),
                    detail,
                    tick,
                    cancel_check=cancel_check,
                )
    finally:
        offsets.close()


def forward_closure_passes(
    source: Path,
    closure: Closure,
    label: str = "Dependency closure",
    quiet: bool = False,
    on_phase: PhaseCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> None:
    """Expand the selection with sequential passes; no offset index required."""
    size = source.stat().st_size
    tick: dict[str, float] = {}
    for iteration in range(1, 64):
        added = 0
        scanned = 0
        progress = Progress(
            f"{label} pass {iteration}",
            size,
            console=not quiet and on_phase is None,
            on_update=(
                None
                if on_phase is None
                else lambda info: _throttled_phase(
                    on_phase,
                    "closure",
                    ((iteration - 1) + float(info["percent"]) / 100.0) / 64.0,
                    str(info.get("detail") or ""),
                    tick,
                    cancel_check=cancel_check,
                )
            ),
        )
        with open_readonly(source) as handle:
            for offset, record in records.iter_records(handle):
                scanned += 1
                if not scanned & 0xFFFF:
                    progress.update(offset, f"{closure.count + added:,} selected")
                entity_id = records.record_id(record)
                if entity_id is None or entity_id not in closure.selected:
                    continue
                if entity_id in closure.filtered_ids:
                    # Aggregate members of a filtered entity are trimmed away on
                    # write, so they must not drag their own closure in here.
                    candidates = split_refs(record)[0]
                else:
                    candidates = records.entity_refs(record)
                for ref in candidates:
                    if closure.selected.add(ref):
                        added += 1
        progress.finish(f"{closure.count + added:,} selected")
        closure.count += added
        if not added:
            return
    if not quiet:
        log("Warning: dependency closure did not settle after 64 passes.")


def backward_pass(
    source: Path,
    closure: Closure,
    groups: tuple[str, ...],
    iterations: int,
    expand: Callable[[list[int]], None],
    work_dir: Path | None = None,
    quiet: bool = False,
    on_phase: PhaseCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> int:
    """Pull in entities that only reference the selection (styles, properties).

    When ``work_dir`` has a candidate id list and an offset index, only those
    candidates are inspected via random access. Otherwise the whole source is
    scanned sequentially (acceptable for small files, far too slow for multi-GB
    assemblies).
    """
    follow: set[str] = set()
    filtered: set[str] = set()
    excluded: set[str] = set()
    for group in groups:
        policy = BACKWARD_GROUPS.get(group)
        if policy is None:
            raise SystemExit(f"Unknown backward group {group!r}.")
        follow |= policy["follow"]
        filtered |= policy["filter"]
        excluded |= policy.get("exclude", set())
    if not follow and not filtered:
        return 0

    use_random = (
        work_dir is not None
        and storage.CandidateList.available(work_dir)
        and model.has_offsets(work_dir)
    )
    if use_random:
        return _backward_pass_random(
            source,
            work_dir,
            closure,
            follow,
            filtered,
            excluded,
            iterations,
            expand,
            quiet=quiet,
            on_phase=on_phase,
            cancel_check=cancel_check,
        )
    if work_dir is not None and model.has_offsets(work_dir) and not quiet:
        log(
            "Warning: no backward-candidate list in the work directory. "
            "Falling back to full-file scans (slow on multi-GB sources). "
            "Run: python3 stepsplit.py enrich <source> --work-dir ..."
        )
    return _backward_pass_sequential(
        source,
        closure,
        follow,
        filtered,
        excluded,
        iterations,
        expand,
        quiet=quiet,
        on_phase=on_phase,
        cancel_check=cancel_check,
    )


def _consider_backward_record(
    record: bytes,
    entity_id: int,
    closure: Closure,
    follow: set[str],
    filtered: set[str],
    excluded: set[str],
    pending: list[int],
) -> bool:
    parsed = records.parse_entity(record)
    types = {name for name, _ in parsed}
    if types & excluded:
        return False
    is_follow = bool(types & follow)
    is_filter = bool(types & filtered)
    if not is_follow and not is_filter:
        return False
    scalar, aggregate = split_refs(record)
    triggers = trigger_refs(parsed)
    if triggers is None:
        triggers = scalar + aggregate
    if not any(ref in closure.selected for ref in triggers):
        return False
    closure.selected.add(entity_id)
    closure.count += 1
    if is_filter and not is_follow:
        closure.filtered_ids.add(entity_id)
        pending.extend(ref for ref in scalar if ref not in closure.selected)
    else:
        pending.extend(ref for ref in scalar + aggregate if ref not in closure.selected)
    return True


# Cached per work directory so batch exports do not re-read the candidate file
# or re-classify millions of entities for every selected node.
_CANDIDATE_IDS: dict[str, list[int]] = {}
_SHORTLIST_CACHE: dict[tuple[str, frozenset[str], frozenset[str]], list[int]] = {}


def clear_candidate_caches(work_dir: Path | None = None) -> None:
    """Drop cached candidate id lists after an index rebuild."""
    if work_dir is None:
        _CANDIDATE_IDS.clear()
        _SHORTLIST_CACHE.clear()
        return
    key = str(work_dir.resolve())
    _CANDIDATE_IDS.pop(key, None)
    for cache_key in list(_SHORTLIST_CACHE):
        if cache_key[0] == key:
            del _SHORTLIST_CACHE[cache_key]


def _all_candidate_ids(work_dir: Path) -> list[int]:
    key = str(work_dir.resolve())
    cached = _CANDIDATE_IDS.get(key)
    if cached is not None:
        return cached
    ids = list(storage.CandidateList.iter_ids(storage.candidates_path(work_dir)))
    _CANDIDATE_IDS[key] = ids
    return ids


def _shortlist_key(
    work_dir: Path, follow: set[str], filtered: set[str], excluded: set[str]
) -> tuple[str, frozenset[str], frozenset[str]]:
    return (
        str(work_dir.resolve()),
        frozenset(follow | filtered),
        frozenset(excluded),
    )


def _backward_pass_random(
    source: Path,
    work_dir: Path,
    closure: Closure,
    follow: set[str],
    filtered: set[str],
    excluded: set[str],
    iterations: int,
    expand: Callable[[list[int]], None],
    quiet: bool = False,
    on_phase: PhaseCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> int:
    needed = follow | filtered
    cache_key = _shortlist_key(work_dir, follow, filtered, excluded)
    typed = _SHORTLIST_CACHE.get(cache_key)
    building = typed is None
    if building:
        pool = _all_candidate_ids(work_dir)
        built: list[int] = []
        if not quiet:
            log(
                f"Backward pass over {len(pool):,} candidates "
                "(building typed filter for reuse)"
            )
    else:
        pool = typed
        built = typed
        if not quiet:
            log(f"Backward pass over {len(pool):,} typed candidates (cached)")
    offsets = storage.OffsetIndex(storage.offsets_path(work_dir), readonly=True)
    total_added = 0
    tick: dict[str, float] = {}
    try:
        with open_readonly(source) as handle:
            for iteration in range(1, iterations + 1):
                scan_list = pool if (building and iteration == 1) else built
                scan_total = max(len(scan_list), 1)
                added = 0
                pending: list[int] = []
                for index, entity_id in enumerate(scan_list, start=1):
                    if cancel_check is not None and index % 2048 == 0:
                        cancel_check()
                    offset = offsets.get(entity_id)
                    if offset is None:
                        continue
                    record = _read_record_at(handle, offset)
                    if building and iteration == 1:
                        types = records.peek_type_names(record)
                        if types & excluded or not (types & needed):
                            continue
                        built.append(entity_id)
                    if entity_id in closure.selected:
                        continue
                    if _consider_backward_record(
                        record, entity_id, closure, follow, filtered, excluded, pending
                    ):
                        added += 1
                    frac = ((iteration - 1) + index / scan_total) / max(iterations, 1)
                    tr = i18n_mod.get_i18n().t
                    detail = tr(
                        "export_backward_detail",
                        pass_n=iteration,
                        passes=iterations,
                        checked=f"{index:,}",
                        total=f"{scan_total:,}",
                        added=f"{total_added + added:,}",
                    )
                    _throttled_phase(
                        on_phase, "backward", frac, detail, tick, cancel_check=cancel_check
                    )
                    if index % 50_000 == 0 and not quiet:
                        log(
                            f"Backward pass {iteration}: checked {index:,}/"
                            f"{scan_total:,}, added {total_added + added:,}"
                        )
                if building and iteration == 1:
                    _SHORTLIST_CACHE[cache_key] = built
                    if not quiet:
                        log(
                            f"Typed filter cached: {len(built):,} of "
                            f"{len(pool):,} candidates"
                        )
                    building = False
                total_added += added
                if not quiet:
                    log(f"Backward pass {iteration}: added {added:,}")
                if pending:
                    expand(pending)
                if not added:
                    break
        _throttled_phase(
            on_phase,
            "backward",
            1.0,
            i18n_mod.get_i18n().t(
                "export_backward_detail",
                pass_n=iterations,
                passes=iterations,
                checked=f"{len(built):,}",
                total=f"{len(built):,}",
                added=f"{total_added:,}",
            ),
            tick,
            force=True,
            cancel_check=cancel_check,
        )
    finally:
        offsets.close()
    return total_added


def _backward_pass_sequential(
    source: Path,
    closure: Closure,
    follow: set[str],
    filtered: set[str],
    excluded: set[str],
    iterations: int,
    expand: Callable[[list[int]], None],
    quiet: bool = False,
    on_phase: PhaseCallback | None = None,
    cancel_check: CancelCheck | None = None,
) -> int:
    markers = tuple({name.encode("ascii") for name in follow | filtered})
    size = source.stat().st_size
    total_added = 0
    tick: dict[str, float] = {}

    for iteration in range(1, iterations + 1):
        added = 0
        scanned = 0
        pending: list[int] = []
        progress = Progress(
            f"Backward pass {iteration}",
            size,
            console=not quiet and on_phase is None,
            on_update=(
                None
                if on_phase is None
                else lambda info: _throttled_phase(
                    on_phase,
                    "backward",
                    ((iteration - 1) + float(info["percent"]) / 100.0) / max(iterations, 1),
                    f"Pass {iteration}/{iterations}: +{total_added + added:,}",
                    tick,
                    cancel_check=cancel_check,
                )
            ),
        )
        with open_readonly(source) as handle:
            for offset, record in records.iter_records(handle):
                scanned += 1
                if not scanned & 0xFFFF:
                    progress.update(offset, f"{total_added + added:,} added")
                if not any(marker in record for marker in markers):
                    continue
                entity_id = records.record_id(record)
                if entity_id is None or entity_id in closure.selected:
                    continue
                if _consider_backward_record(
                    record, entity_id, closure, follow, filtered, excluded, pending
                ):
                    added += 1
        progress.finish(f"{total_added + added:,} added")
        total_added += added
        if pending:
            expand(pending)
        if not added:
            break
    return total_added


def read_source_header(source: Path) -> dict[str, bytes]:
    """Return the FILE_DESCRIPTION and FILE_SCHEMA records of the source."""
    header: dict[str, bytes] = {}
    with open_readonly(source) as handle:
        for _, record in records.iter_records(handle):
            stripped = record.strip()
            upper = stripped.upper()
            if upper.startswith(b"FILE_DESCRIPTION"):
                header["description"] = stripped
            elif upper.startswith(b"FILE_SCHEMA"):
                header["schema"] = stripped
            elif upper.startswith(b"FILE_NAME"):
                header["name"] = stripped
            elif upper == b"ENDSEC;" or upper == b"DATA;":
                break
    return header


def _escape(text: str) -> bytes:
    return text.replace("'", "''").encode("latin-1", "replace")


def build_header(source_header: dict[str, bytes], title: str, source: Path) -> bytes:
    timestamp = _datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    description = source_header.get("description", b"FILE_DESCRIPTION((''),'2;1');")
    schema = source_header.get(
        "schema", b"FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));"
    )
    lines = [
        b"ISO-10303-21;",
        b"HEADER;",
        description,
        b"FILE_NAME('"
        + _escape(title)
        + b"','"
        + _escape(timestamp)
        + b"',(''),(''),'stepsplit "
        + _escape(VERSION)
        + b"','"
        + _escape(source.name)
        + b"','');",
        schema,
        b"ENDSEC;",
        b"DATA;",
    ]
    return b"\n".join(lines) + b"\n"


def write_step(
    source: Path,
    output: Path,
    closure: Closure,
    header: bytes,
    dry_run: bool = False,
    work_dir: Path | None = None,
    quiet: bool = False,
    on_write_progress: Callable[[int, int], None] | None = None,
    cancel_check: CancelCheck | None = None,
) -> tuple[int, int, int]:
    """Copy the selected records in original order. Returns (written, dropped, bytes).

    With an offset index the writer seeks only to selected entities (sorted by
    byte offset). That keeps a small export proportional to the subtree size
    instead of the whole source file.
    """
    if work_dir is not None and model.has_offsets(work_dir):
        return _write_step_by_offset(
            source,
            work_dir,
            output,
            closure,
            header,
            dry_run,
            quiet=quiet,
            on_write_progress=on_write_progress,
            cancel_check=cancel_check,
        )
    return _write_step_sequential(
        source,
        output,
        closure,
        header,
        dry_run,
        quiet=quiet,
        on_write_progress=on_write_progress,
        cancel_check=cancel_check,
    )


def _emit_payload(
    record: bytes, entity_id: int, closure: Closure
) -> bytes | None:
    payload = record.strip()
    if entity_id in closure.filtered_ids:
        trimmed = records.filter_reference_lists(payload, closure.selected)
        if trimmed is None:
            return None
        payload = trimmed
    return payload + b"\n"


def _write_step_by_offset(
    source: Path,
    work_dir: Path,
    output: Path,
    closure: Closure,
    header: bytes,
    dry_run: bool,
    quiet: bool = False,
    on_write_progress: Callable[[int, int], None] | None = None,
    cancel_check: CancelCheck | None = None,
) -> tuple[int, int, int]:
    offsets = storage.OffsetIndex(storage.offsets_path(work_dir), readonly=True)
    pairs: list[tuple[int, int]] = []
    for entity_id in closure.selected.iter_set():
        offset = offsets.get(entity_id)
        if offset is not None:
            pairs.append((offset, entity_id))
    pairs.sort()
    if not quiet:
        log(f"Writing {len(pairs):,} entities via offset index")

    written = 0
    dropped = 0
    total = len(header)
    footer = b"ENDSEC;\nEND-ISO-10303-21;\n"
    destination = None
    total_pairs = len(pairs)
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        destination = output.open("wb", buffering=8 << 20)
        destination.write(header)
    try:
        with open_readonly(source) as handle:
            for index, (offset, entity_id) in enumerate(pairs, start=1):
                if cancel_check is not None and index % 2048 == 0:
                    cancel_check()
                record = _read_record_at(handle, offset)
                payload = _emit_payload(record, entity_id, closure)
                if payload is None:
                    dropped += 1
                    continue
                total += len(payload)
                written += 1
                if destination is not None:
                    destination.write(payload)
                if on_write_progress is not None and (index % 500 == 0 or index == total_pairs):
                    on_write_progress(index, total_pairs)
                elif index % 50_000 == 0 and not quiet:
                    log(f"Writing: {index:,}/{total_pairs:,}")
        total += len(footer)
        if destination is not None:
            destination.write(footer)
    finally:
        if destination is not None:
            destination.close()
        offsets.close()
    return written, dropped, total


def _write_step_sequential(
    source: Path,
    output: Path,
    closure: Closure,
    header: bytes,
    dry_run: bool = False,
    quiet: bool = False,
    on_write_progress: Callable[[int, int], None] | None = None,
    cancel_check: CancelCheck | None = None,
) -> tuple[int, int, int]:
    size = source.stat().st_size
    written = 0
    dropped = 0
    total = len(header)
    footer = b"ENDSEC;\nEND-ISO-10303-21;\n"

    destination = None
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        destination = output.open("wb", buffering=8 << 20)
        destination.write(header)

    scanned = 0
    progress = Progress("Writing" if not dry_run else "Estimating", size, console=not quiet)
    try:
        with open_readonly(source) as handle:
            for offset, record in records.iter_records(handle):
                scanned += 1
                if cancel_check is not None and scanned % 2048 == 0:
                    cancel_check()
                if not scanned & 0xFFFF:
                    progress.update(offset, f"{written:,} entities")
                    if on_write_progress is not None:
                        on_write_progress(written, closure.count or 1)
                entity_id = records.record_id(record)
                if entity_id is None or entity_id not in closure.selected:
                    continue
                payload = _emit_payload(record, entity_id, closure)
                if payload is None:
                    dropped += 1
                    continue
                total += len(payload)
                written += 1
                if destination is not None:
                    destination.write(payload)
        total += len(footer)
        if destination is not None:
            destination.write(footer)
    finally:
        if destination is not None:
            destination.close()
    progress.finish(f"{written:,} entities")
    if on_write_progress is not None:
        on_write_progress(written, max(written, 1))
    return written, dropped, total


def export_node(
    source: Path,
    work_dir: Path,
    connection: sqlite3.Connection,
    node: model.Node,
    output: Path,
    closure_mode: str = "auto",
    backward_groups: tuple[str, ...] = DEFAULT_BACKWARD_GROUPS,
    backward_iterations: int = 3,
    dry_run: bool = False,
    overwrite: bool = False,
    resume: bool = False,
    quiet: bool = False,
    on_phase: Callable[[str, float, str], None] | None = None,
    on_write_progress: Callable[[int, int], None] | None = None,
    cancel_check: CancelCheck | None = None,
) -> ExportResult:
    """Export one product definition and everything below it."""

    def emit(message: str = "") -> None:
        if not quiet and message:
            log(message)

    def phase(step: str, fraction: float = 0.0, detail: str = "") -> None:
        if cancel_check is not None:
            cancel_check()
        if on_phase is not None:
            on_phase(step, fraction, detail)

    if not dry_run:
        guard_output_path(source, output, overwrite)

    product_definitions, usages = model.subtree(connection, node.pd_id)
    meta = storage.read_meta(connection)
    max_id = int(meta.get("scan_max_id", 0))
    if not max_id:
        raise SystemExit("The index does not record a maximum entity id; rebuild it.")

    if closure_mode == "auto":
        closure_mode = "random" if model.has_offsets(work_dir) else "passes"
    if closure_mode == "random" and not model.has_offsets(work_dir):
        raise SystemExit(
            "Closure mode 'random' needs the offset index. Re-run 'index' without "
            "--structure-only, or use --closure-mode passes."
        )

    state_dir = work_dir / "exports" / f"pd{node.pd_id}"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "state.json"
    previous = {}
    if resume and state_file.exists():
        previous = json.loads(state_file.read_text())
        if previous.get("closure_mode") != closure_mode:
            previous = {}

    reuse = bool(previous)
    selected = storage.BitSet(state_dir / "selected.bitset", max_id, reuse=reuse)
    closure = Closure(selected=selected, count=int(previous.get("count", 0)))
    closure.filtered_ids = set(previous.get("filtered_ids", []))

    emit(
        f"Subtree {node.name} [PD #{node.pd_id}]: "
        f"{len(product_definitions):,} product definitions, {len(usages):,} usages"
    )
    phase("prepare", 1.0)

    queue = storage.DiskQueue(state_dir / "queue.u64", resume=reuse)
    try:
        phase("closure", 0.0)
        if reuse:
            queue.read_position = int(previous.get("queue_read_position", 0))
            emit(f"Resuming closure with {queue.pending:,} queued entities")
        else:
            seeds = structural_seeds(connection, product_definitions, usages)
            fresh = [seed for seed in sorted(seeds) if closure.selected.add(seed)]
            closure.count += len(fresh)
            queue.extend(fresh)

        def expand(additional: list[int]) -> None:
            fresh_ids = [ref for ref in additional if closure.selected.add(ref)]
            closure.count += len(fresh_ids)
            if not fresh_ids:
                return
            if closure_mode == "random":
                queue.extend(fresh_ids)
                forward_closure_random(
                    source,
                    work_dir,
                    closure,
                    queue,
                    quiet=quiet,
                    on_phase=on_phase,
                    cancel_check=cancel_check,
                )
            else:
                forward_closure_passes(
                    source,
                    closure,
                    quiet=quiet,
                    on_phase=on_phase,
                    cancel_check=cancel_check,
                )

        if closure_mode == "random":
            forward_closure_random(
                source,
                work_dir,
                closure,
                queue,
                quiet=quiet,
                on_phase=on_phase,
                cancel_check=cancel_check,
            )
        else:
            forward_closure_passes(
                source,
                closure,
                quiet=quiet,
                on_phase=on_phase,
                cancel_check=cancel_check,
            )

        phase("closure", 1.0, f"{closure.count:,} selected")
        _save_state(state_file, closure, queue, closure_mode)

        phase("backward", 0.0)
        if backward_groups:
            added = backward_pass(
                source,
                closure,
                backward_groups,
                backward_iterations,
                expand,
                work_dir=work_dir,
                quiet=quiet,
                on_phase=on_phase,
                cancel_check=cancel_check,
            )
            emit(f"Backward passes added {added:,} entities")
            phase("backward", 1.0, f"+{added:,}")
            _save_state(state_file, closure, queue, closure_mode)
            if "geometry" in backward_groups and added == 0:
                shaped = connection.execute(
                    "SELECT 1 FROM definition_shapes WHERE definition_id IN ({}) LIMIT 1".format(
                        ",".join("?" * min(len(product_definitions), 200))
                    ),
                    list(product_definitions)[:200],
                ).fetchone()
                if shaped:
                    emit(
                        "Warning: no backward geometry links were added, but the subtree "
                        "has shape data. The STEP file may open empty in a CAD viewer."
                    )

        if closure.missing_offsets:
            emit(
                f"Warning: {len(closure.missing_offsets):,} referenced entities are not "
                f"in the index (first: {closure.missing_offsets[:5]})."
            )

        header = build_header(read_source_header(source), node.name, source)
        phase("write", 0.0)
        written, dropped, size = write_step(
            source,
            output,
            closure,
            header,
            dry_run,
            work_dir=work_dir,
            quiet=quiet,
            on_write_progress=on_write_progress,
            cancel_check=cancel_check,
        )
        phase("write", 1.0, f"{written:,} entities")
    finally:
        queue.flush()
        queue.close()
        selected.close()

    if not dry_run:
        for leftover in (state_file, state_dir / "queue.u64", state_dir / "selected.bitset"):
            leftover.unlink(missing_ok=True)

    return ExportResult(
        output=output,
        product=node.name,
        pd_id=node.pd_id,
        product_definitions=len(product_definitions),
        usages=len(usages),
        entities=closure.count,
        written=written,
        dropped=dropped,
        bytes_written=size,
        dry_run=dry_run,
    )


def _save_state(
    state_file: Path, closure: Closure, queue: storage.DiskQueue, closure_mode: str
) -> None:
    closure.selected.flush()
    queue.flush()
    state_file.write_text(
        json.dumps(
            {
                "count": closure.count,
                "queue_read_position": queue.read_position,
                "closure_mode": closure_mode,
                "filtered_ids": sorted(closure.filtered_ids),
            }
        )
    )


def output_path_for(node: model.Node, directory: Path, suffix: str = ".step") -> Path:
    return directory / f"{safe_filename(node.name)}{suffix}"


def describe(result: ExportResult) -> str:
    verb = "Would write" if result.dry_run else "Wrote"
    lines = [
        f"{verb} {result.output}",
        f"  product            {result.product} [PD #{result.pd_id}]",
        f"  subtree            {result.product_definitions:,} product definitions, "
        f"{result.usages:,} usages",
        f"  entities selected  {result.entities:,}",
        f"  entities written   {result.written:,}",
        f"  size               {format_bytes(result.bytes_written)}",
    ]
    if result.dropped:
        lines.append(f"  dropped aggregates {result.dropped:,}")
    return "\n".join(lines)
