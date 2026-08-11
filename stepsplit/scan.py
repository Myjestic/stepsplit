"""Single sequential pass over a STEP file that builds the disk-backed indexes.

The pass is restartable: byte offset, entity counters and the structure tables
are committed together, so an aborted run continues at the last checkpoint
instead of starting over.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from . import VERSION, records, storage
from . import i18n as i18n_mod
from .util import Progress, ProgressCallback, log


def _fmt_int(value: int) -> str:
    text = f"{value:,}"
    if i18n_mod.get_i18n().language == "de":
        return text.replace(",", ".")
    return text


def new_index_build_id() -> str:
    """Human-readable stamp for one completed index build (local time)."""
    return time.strftime("%Y%m%d-%H%M%S")

# A record is only parsed in full when it contains one of these markers.
STRUCTURE_MARKERS = (
    b"PRODUCT",
    b"ASSEMBLY",
    b"SHAPE_DEFINITION_REPRESENTATION",
    b"CONTEXT_DEPENDENT",
    b"REPRESENTATION_RELATIONSHIP",
)

# Cheap byte markers for entities that a backward export pass may need. Matching
# only stores the entity id; the export later decides with the real type name.
BACKWARD_CANDIDATE_MARKERS = (
    b"SHAPE_REPRESENTATION_RELATIONSHIP",
    b"CONSTRUCTIVE_GEOMETRY_REPRESENTATION_RELATIONSHIP",
    b"SHAPE_DEFINITION_REPRESENTATION",
    b"STYLED_ITEM",
    b"OVER_RIDING_STYLED_ITEM",
    b"ANNOTATION_OCCURRENCE",
    b"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION",
    b"PRESENTATION_LAYER_ASSIGNMENT",
    b"APPLICATION_PROTOCOL_DEFINITION",
    b"PRODUCT_RELATED_PRODUCT_CATEGORY",
    b"PRODUCT_CATEGORY_RELATIONSHIP",
    b"PROPERTY_DEFINITION",
    b"PROPERTY_DEFINITION_REPRESENTATION",
    b"SHAPE_ASPECT",
    b"SHAPE_ASPECT_RELATIONSHIP",
    b"GENERAL_PROPERTY_ASSOCIATION",
)

USAGE_TYPES = {
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
    "ASSEMBLY_COMPONENT_USAGE",
    "SPECIFIED_HIGHER_USAGE_OCCURRENCE",
    "PRODUCT_DEFINITION_USAGE",
}

FORMATION_TYPES = {
    "PRODUCT_DEFINITION_FORMATION",
    "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE",
}

# Types that make a record look like a PRODUCT_DEFINITION without being one.
PD_EXCLUSIONS = FORMATION_TYPES | {
    "PRODUCT_DEFINITION_SHAPE",
    "PRODUCT_DEFINITION_RELATIONSHIP",
    "PRODUCT_DEFINITION_USAGE",
    "PRODUCT_DEFINITION_CONTEXT",
    "PRODUCT_DEFINITION_EFFECTIVITY",
}

CHECKPOINT_BYTES = 256 << 20


@dataclass
class ScanCounters:
    entities: int = 0
    products: int = 0
    formations: int = 0
    product_definitions: int = 0
    usages: int = 0
    definition_shapes: int = 0
    shape_representations: int = 0
    context_shapes: int = 0
    max_id: int = 0
    usage_fallbacks: int = 0
    backward_candidates: int = 0


def is_backward_candidate(record: bytes) -> bool:
    return any(marker in record for marker in BACKWARD_CANDIDATE_MARKERS)


def fingerprint(source: Path) -> dict[str, str]:
    """Identify the source by size, mtime and hashes of its head and tail."""
    stat = source.stat()
    head = hashlib.sha256()
    tail = hashlib.sha256()
    window = 1 << 16
    with source.open("rb") as handle:
        head.update(handle.read(window))
        if stat.st_size > window:
            handle.seek(max(stat.st_size - window, 0))
            tail.update(handle.read(window))
    return {
        "source_size": str(stat.st_size),
        "source_mtime_ns": str(stat.st_mtime_ns),
        "source_head_sha256": head.hexdigest(),
        "source_tail_sha256": tail.hexdigest(),
    }


def verify_fingerprint(connection: sqlite3.Connection, source: Path) -> None:
    stored = storage.read_meta(connection)
    current = fingerprint(source)
    for key, value in current.items():
        if key in stored and stored[key] != value:
            raise SystemExit(
                f"The source file changed since the index was built ({key} differs).\n"
                f"Rebuild the index with --force."
            )


def _store_usage(
    connection: sqlite3.Connection,
    entity_id: int,
    parsed: list[tuple[str, list[bytes]]],
    usage_type: str,
    counters: ScanCounters,
) -> None:
    """Persist an assembly usage using positional AP214 arguments.

    ``PRODUCT_DEFINITION_RELATIONSHIP`` defines the arguments
    ``(id, name, description, relating_product_definition,
    related_product_definition)``. Complex instances keep those arguments on the
    relationship sub-entity, so it is preferred when present.
    """
    arguments: list[bytes] = []
    for name, args in parsed:
        if name == "PRODUCT_DEFINITION_RELATIONSHIP" and len(args) >= 5:
            arguments = args
            break
        if name == usage_type and len(args) >= 5:
            arguments = args
    parent = child = None
    mode = "positional"
    if len(arguments) >= 5:
        parent = records.argument_ref(arguments[3])
        child = records.argument_ref(arguments[4])
    if parent is None or child is None:
        refs = [
            records.argument_ref(argument)
            for _, args in parsed
            for argument in args
        ]
        refs = [ref for ref in refs if ref is not None]
        if len(refs) < 2:
            return
        parent, child = refs[-2], refs[-1]
        mode = "trailing-refs"
        counters.usage_fallbacks += 1

    designator = ""
    if len(arguments) >= 3:
        designator = records.decode_step_string(arguments[2])[:120]

    connection.execute(
        "INSERT OR REPLACE INTO usages"
        "(usage_id,parent_pd,child_pd,usage_type,designator,parse_mode)"
        " VALUES(?,?,?,?,?,?)",
        (entity_id, parent, child, usage_type, designator, mode),
    )
    counters.usages += 1


def store_structure(
    connection: sqlite3.Connection, entity_id: int, record: bytes, counters: ScanCounters
) -> None:
    parsed = records.parse_entity(record)
    if not parsed:
        return
    types = {name for name, _ in parsed}
    arguments = {name: args for name, args in parsed}

    if "PRODUCT" in types:
        args = arguments["PRODUCT"]
        if len(args) >= 2:
            connection.execute(
                "INSERT OR REPLACE INTO products(product_id,ident,name) VALUES(?,?,?)",
                (
                    entity_id,
                    records.decode_step_string(args[0]),
                    records.decode_step_string(args[1]) or records.decode_step_string(args[0]),
                ),
            )
            counters.products += 1

    formation_type = next((name for name in FORMATION_TYPES if name in types), None)
    if formation_type:
        args = arguments[formation_type]
        product = records.argument_ref(args[2]) if len(args) >= 3 else None
        if product is not None:
            connection.execute(
                "INSERT OR REPLACE INTO formations(formation_id,product_id) VALUES(?,?)",
                (entity_id, product),
            )
            counters.formations += 1

    if "PRODUCT_DEFINITION" in types and not types & PD_EXCLUSIONS:
        args = arguments["PRODUCT_DEFINITION"]
        formation = records.argument_ref(args[2]) if len(args) >= 3 else None
        if formation is not None:
            connection.execute(
                "INSERT OR REPLACE INTO product_definitions(pd_id,formation_id) VALUES(?,?)",
                (entity_id, formation),
            )
            counters.product_definitions += 1

    usage_type = next((name for name, _ in parsed if name in USAGE_TYPES), None)
    if usage_type:
        _store_usage(connection, entity_id, parsed, usage_type, counters)

    if "PRODUCT_DEFINITION_SHAPE" in types:
        args = arguments["PRODUCT_DEFINITION_SHAPE"] or arguments.get("PROPERTY_DEFINITION", [])
        definition = records.argument_ref(args[2]) if len(args) >= 3 else None
        if definition is not None:
            connection.execute(
                "INSERT OR REPLACE INTO definition_shapes(pds_id,definition_id) VALUES(?,?)",
                (entity_id, definition),
            )
            counters.definition_shapes += 1

    if "SHAPE_DEFINITION_REPRESENTATION" in types:
        args = arguments["SHAPE_DEFINITION_REPRESENTATION"]
        if not args:
            args = arguments.get("REPRESENTATION_RELATIONSHIP", [])
        if len(args) >= 2:
            definition = records.argument_ref(args[0])
            representation = records.argument_ref(args[1])
            if definition is not None and representation is not None:
                connection.execute(
                    "INSERT OR REPLACE INTO shape_representations"
                    "(sdr_id,pds_id,representation_id) VALUES(?,?,?)",
                    (entity_id, definition, representation),
                )
                counters.shape_representations += 1

    if "CONTEXT_DEPENDENT_SHAPE_REPRESENTATION" in types:
        args = arguments["CONTEXT_DEPENDENT_SHAPE_REPRESENTATION"]
        if len(args) >= 2:
            relationship = records.argument_ref(args[0])
            definition = records.argument_ref(args[1])
            if relationship is not None and definition is not None:
                connection.execute(
                    "INSERT OR REPLACE INTO context_shapes"
                    "(cdsr_id,relationship_id,pds_id) VALUES(?,?,?)",
                    (entity_id, relationship, definition),
                )
                counters.context_shapes += 1


def _load_counters(meta: dict[str, str]) -> ScanCounters:
    counters = ScanCounters()
    for field in counters.__dataclass_fields__:
        value = meta.get(f"scan_{field}")
        if value is not None:
            setattr(counters, field, int(value))
    return counters


def _checkpoint(
    connection: sqlite3.Connection,
    offsets: storage.OffsetIndex | None,
    offset: int,
    counters: ScanCounters,
    state: str,
) -> None:
    if offsets is not None:
        offsets.flush()
    values: dict[str, object] = {
        "scan_offset": offset,
        "scan_state": state,
        "version": VERSION,
    }
    for field in counters.__dataclass_fields__:
        values[f"scan_{field}"] = getattr(counters, field)
    storage.write_meta(connection, values)
    connection.commit()
    connection.execute("BEGIN")


def build_index(
    source: Path,
    work_dir: Path,
    with_offsets: bool = True,
    force: bool = False,
    resume: bool = True,
    on_progress: ProgressCallback | None = None,
    quiet: bool = False,
) -> ScanCounters:
    """Scan ``source`` and populate the structure tables and offset index."""
    from . import export as export_module

    work_dir.mkdir(parents=True, exist_ok=True)
    database = storage.structure_db_path(work_dir)
    offsets_file = storage.offsets_path(work_dir)
    export_module.clear_candidate_caches(work_dir)

    def emit(message: str) -> None:
        if not quiet:
            log(message)

    if force:
        database.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        offsets_file.unlink(missing_ok=True)
        storage.candidates_path(work_dir).unlink(missing_ok=True)

    connection = storage.connect(work_dir, create=True)
    meta = storage.read_meta(connection)
    start_offset = 0
    counters = ScanCounters()

    if meta:
        verify_fingerprint(connection, source)
        state = meta.get("scan_state")
        had_offsets = meta.get("scan_with_offsets") == "True"
        if state == "complete" and (had_offsets or not with_offsets):
            connection.close()
            raise SystemExit(
                f"A complete index already exists in {work_dir}. Use --force to rebuild it."
            )
        if resume and state == "running" and had_offsets == with_offsets:
            start_offset = int(meta.get("scan_offset", 0))
            counters = _load_counters(meta)
            emit(
                f"Resuming scan at byte {start_offset:,} "
                f"({counters.entities:,} entities done)"
            )
        elif state is not None:
            emit("Previous index is incomplete or uses different options; restarting the scan.")
            connection.close()
            return build_index(
                source,
                work_dir,
                with_offsets,
                force=True,
                resume=False,
                on_progress=on_progress,
                quiet=quiet,
            )

    offsets: storage.OffsetIndex | None = None
    if with_offsets:
        offsets = storage.OffsetIndex(offsets_file, capacity=counters.max_id)

    candidates = storage.CandidateList(
        storage.candidates_path(work_dir), append=start_offset > 0
    )

    source_size = source.stat().st_size
    tr = i18n_mod.get_i18n().t
    progress = Progress(
        tr("scan_progress_label"),
        source_size,
        start=start_offset,
        on_update=on_progress,
    )
    storage.write_meta(
        connection,
        {**fingerprint(source), "scan_with_offsets": with_offsets, "source": str(source.resolve())},
    )
    connection.commit()
    connection.execute("BEGIN")

    next_checkpoint = start_offset + CHECKPOINT_BYTES
    resume_offset = start_offset
    started = time.monotonic()

    try:
        with source.open("rb") as handle:
            for offset, record in records.iter_records(handle, start=start_offset):
                # resume_offset still points behind the previous record, so an
                # interrupt in the middle of this one replays it instead of
                # losing it.
                if resume_offset >= next_checkpoint:
                    candidates.flush()
                    _checkpoint(connection, offsets, resume_offset, counters, "running")
                    next_checkpoint = resume_offset + CHECKPOINT_BYTES

                entity_id = records.record_id(record)
                if entity_id is not None:
                    counters.entities += 1
                    if entity_id > counters.max_id:
                        counters.max_id = entity_id
                    if offsets is not None:
                        offsets.set(entity_id, offset)
                    if is_backward_candidate(record):
                        candidates.add(entity_id)
                        counters.backward_candidates += 1
                    for marker in STRUCTURE_MARKERS:
                        if marker in record:
                            store_structure(connection, entity_id, record, counters)
                            break
                resume_offset = offset + len(record)
                progress.update(
                    resume_offset,
                    tr(
                        "scan_progress_detail",
                        entities=_fmt_int(counters.entities),
                        usages=_fmt_int(counters.usages),
                    ),
                )
        candidates.flush()
        _checkpoint(connection, offsets, source_size, counters, "complete")
        storage.write_meta(connection, {"index_build_id": new_index_build_id()})
        connection.commit()
        connection.execute("BEGIN")
    except KeyboardInterrupt:
        candidates.flush()
        _checkpoint(connection, offsets, resume_offset, counters, "running")
        emit(
            f"\nInterrupted at byte {resume_offset:,}. "
            "Re-run the same command to resume."
        )
        raise
    finally:
        connection.commit()
        connection.close()
        candidates.close()
        if offsets is not None:
            offsets.close()

    progress.finish(tr("scan_progress_finish", entities=_fmt_int(counters.entities)))
    emit(
        tr(
            "scan_done_log",
            seconds=time.monotonic() - started,
            entities=_fmt_int(counters.entities),
            max_id=_fmt_int(counters.max_id),
        )
    )
    return counters


def enrich_candidates(
    source: Path,
    work_dir: Path,
    force: bool = False,
    on_progress: ProgressCallback | None = None,
) -> int:
    """Build only the backward-candidate id list for an already complete index.

    Needed once for indexes created before candidate collection existed. One
    sequential read of the source; the offset index and structure tables stay.
    """
    from . import export as export_module

    connection = storage.connect(work_dir)
    verify_fingerprint(connection, source)
    meta = storage.read_meta(connection)
    if meta.get("scan_state") != "complete":
        connection.close()
        raise SystemExit("The structure index is incomplete; run 'index' first.")
    path = storage.candidates_path(work_dir)
    if path.exists() and not force:
        connection.close()
        raise SystemExit(
            f"Candidate list already exists at {path}. Use --force to rebuild it."
        )
    connection.close()
    export_module.clear_candidate_caches(work_dir)

    source_size = source.stat().st_size
    tr = i18n_mod.get_i18n().t
    progress = Progress(tr("scan_enrich_label"), source_size, on_update=on_progress)
    count = 0
    scanned = 0
    with storage.CandidateList(path) as candidates, source.open("rb") as handle:
        for offset, record in records.iter_records(handle):
            scanned += 1
            entity_id = records.record_id(record)
            detail = tr(
                "scan_enrich_detail",
                count=_fmt_int(count),
                scanned=_fmt_int(scanned),
            )
            if entity_id is None:
                progress.update(offset, detail)
                continue
            if is_backward_candidate(record):
                candidates.add(entity_id)
                count += 1
            # Update by time/bytes, not by candidate milestones — otherwise the
            # bar freezes while scanning geometry-heavy regions.
            progress.update(
                offset,
                tr(
                    "scan_enrich_detail",
                    count=_fmt_int(count),
                    scanned=_fmt_int(scanned),
                ),
            )
    progress.finish(tr("scan_enrich_finish", count=_fmt_int(count)))
    connection = storage.connect(work_dir)
    storage.write_meta(
        connection,
        {
            "scan_backward_candidates": count,
            "index_build_id": new_index_build_id(),
        },
    )
    connection.commit()
    connection.close()
    log(f"Fertig: {_fmt_int(count)} → {path}")
    return count
