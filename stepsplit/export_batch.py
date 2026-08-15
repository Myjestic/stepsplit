"""Multi-node export with optional parallelism and progress reporting."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import export as export_module
from . import model, storage, validate
from .export import ExportCancelled
from .util import ProgressCallback, log, safe_filename

ProgressState = dict[str, object]

_EXPORT_PHASES: tuple[tuple[str, float], ...] = (
    ("prepare", 0.05),
    ("closure", 0.35),
    ("backward", 0.25),
    ("write", 0.30),
    ("done", 0.05),
)


def index_export_id(connection) -> str:
    """Folder name for this index generation.

    Prefer the human-readable ``index_build_id`` written when a scan finishes
    (``YYYYMMDD-HHMMSS``). Older indexes use the structure-DB mtime as a dated
    stand-in so the folder stays readable until the next rebuild.
    """
    meta = storage.read_meta(connection)
    build_id = meta.get("index_build_id", "").strip()
    if build_id:
        return safe_filename(build_id)
    try:
        row = connection.execute("PRAGMA database_list").fetchone()
        db_path = Path(row[2]) if row and row[2] else None
        if db_path and db_path.is_file():
            return time.strftime(
                "%Y%m%d-%H%M%S", time.localtime(db_path.stat().st_mtime)
            )
    except OSError:
        pass
    head = meta.get("source_head_sha256", "")
    if head:
        return f"legacy-{head[:8]}"
    return f"legacy-{meta.get('source_size', '0')}"


def write_export_index_note(
    index_dir: Path,
    source: Path,
    connection,
) -> None:
    """Leave a short README so the dated folder is self-explanatory."""
    index_dir.mkdir(parents=True, exist_ok=True)
    note = index_dir / "INDEX.txt"
    if note.exists():
        return
    meta = storage.read_meta(connection)
    lines = [
        "StepSplit export folder for one index build",
        "",
        f"Source file:     {source}",
        f"Index build id:  {meta.get('index_build_id') or index_export_id(connection)}",
        f"Tool version:    {meta.get('version', '')}",
        f"Source size:     {meta.get('source_size', '')} bytes",
        f"Source head:     {meta.get('source_head_sha256', '')}",
        f"Source tail:     {meta.get('source_tail_sha256', '')}",
        "",
        "A new index rebuild (or candidate enrich) creates a new sibling folder",
        "with a fresh build id, so exports from different index generations stay",
        "separated.",
        "",
    ]
    note.write_text("\n".join(lines), encoding="utf-8")


def _step_path_for_name(
    directory: Path,
    name: str,
    used: set[Path] | None = None,
    *,
    sequence: int | None = None,
) -> Path:
    """``{name}.step`` or ``{n}_{name}.step``; ``_2`` only on in-batch collisions."""
    base = safe_filename(name)
    if sequence is not None and sequence > 0:
        base = f"{sequence}_{base}"
    candidate = directory / f"{base}.step"
    if used is None:
        return candidate
    index = 2
    while candidate in used:
        candidate = directory / f"{base}_{index}.step"
        index += 1
    used.add(candidate)
    return candidate


def folder_parts_for_node(connection, node: model.Node) -> tuple[str, ...]:
    """Assembly folders from tree root down to the node's parent."""
    if node.path_parts:
        return node.path_parts
    chain = model.path_to_root(connection, node.pd_id)
    if len(chain) <= 1:
        return ()
    names = model.names_for_pds(connection, chain[:-1])
    return tuple(safe_filename(names[pd_id]) for pd_id in chain[:-1])


def output_path_for(
    node: model.Node,
    export_base: Path,
    source: Path,
    connection,
    *,
    used_paths: set[Path] | None = None,
    sequence: int | None = None,
) -> Path:
    """Path: ``{base}/{source}/{index_build}/{…folders}/{[n_]name}.step``."""
    build_id = index_export_id(connection)
    folders = folder_parts_for_node(connection, node)
    index_dir = export_base / safe_filename(source.name) / build_id
    write_export_index_note(index_dir, source, connection)
    directory = index_dir.joinpath(*folders)
    return _step_path_for_name(directory, node.name, used_paths, sequence=sequence)


@dataclass
class NodeProgress:
    """Maps per-node phases onto one 0-1 fraction for a single export."""

    reporter: Callable[[ProgressState], None] | None
    node_name: str
    node_index: int
    node_total: int

    def _phase_base(self, step: str) -> float:
        order = {name: index for index, (name, _) in enumerate(_EXPORT_PHASES)}
        idx = order.get(step, 0)
        return sum(weight for name, weight in _EXPORT_PHASES[:idx])

    def _phase_weight(self, step: str) -> float:
        for name, weight in _EXPORT_PHASES:
            if name == step:
                return weight
        return 0.05

    def _emit(self, step: str, fraction: float, detail: str = "") -> None:
        if self.reporter is None:
            return
        # Percent is local to this node (0-100), so parallel exports can
        # each keep their own bar without overwriting each other.
        node_frac = self._phase_base(step) + fraction * self._phase_weight(step)
        self.reporter(
            {
                "step": step,
                "percent": min(node_frac * 100.0, 100.0),
                "detail": detail,
                "node": self.node_name,
                "node_index": self.node_index + 1,
                "node_total": self.node_total,
                "slot": self.node_index,
            }
        )

    def phase(self, step: str, detail: str = "") -> None:
        self._emit(step, 0.0, detail)

    def update(self, step: str, fraction: float, detail: str = "") -> None:
        self._emit(step, fraction, detail)

    def done(self) -> None:
        self._emit("done", 1.0, "")


def _export_one(
    source: Path,
    work_dir: Path,
    node: model.Node,
    destination: Path,
    *,
    closure_mode: str,
    backward_groups: tuple[str, ...],
    backward_iterations: int,
    dry_run: bool,
    overwrite: bool,
    resume: bool,
    skip_check: bool,
    reporter: Callable[[ProgressState], None] | None,
    node_index: int,
    node_total: int,
    cancel: threading.Event,
) -> export_module.ExportResult:
    progress = NodeProgress(reporter, node.name, node_index, node_total)
    progress.phase("prepare")
    connection = storage.connect_readonly(work_dir)

    def cancel_check() -> None:
        if cancel.is_set():
            raise ExportCancelled()

    def on_write(written: int, total: int) -> None:
        cancel_check()
        if total:
            progress.update("write", written / total, f"{written:,} / {total:,}")

    try:
        progress.phase("closure")
        result = export_module.export_node(
            source,
            work_dir,
            connection,
            node,
            destination,
            closure_mode=closure_mode,
            backward_groups=backward_groups,
            backward_iterations=backward_iterations,
            dry_run=dry_run,
            overwrite=overwrite,
            resume=resume,
            quiet=True,
            on_phase=lambda step, frac, detail="": progress.update(step, frac, detail),
            on_write_progress=on_write,
            cancel_check=cancel_check,
        )
    finally:
        connection.close()

    if cancel.is_set():
        raise ExportCancelled()

    if not dry_run and not skip_check:
        progress.phase("done", "validate")
        check = validate.validate_step_file(destination)
        if not check.ok:
            raise SystemExit(check.render())

    progress.done()
    return result


def export_nodes(
    source: Path,
    work_dir: Path,
    connection,
    nodes: list[model.Node],
    export_dir: Path,
    *,
    closure_mode: str = "auto",
    backward_groups: tuple[str, ...] = export_module.DEFAULT_BACKWARD_GROUPS,
    backward_iterations: int = 3,
    dry_run: bool = False,
    overwrite: bool = False,
    resume: bool = False,
    skip_check: bool = False,
    parallel: bool = False,
    max_workers: int | None = 1,
    on_progress: ProgressCallback | None = None,
    single_output: Path | None = None,
    cancel: threading.Event | None = None,
    numbered: bool = False,
) -> tuple[list[export_module.ExportResult], int]:
    """Export many nodes; returns results and failure count.

    One Ctrl+C sets a shared cancel flag so all workers stop cooperatively
    without traceback spam or requiring multiple interrupts.

    All selected nodes are exported. By default exports run one after another:
    concurrent random I/O on one large STEP file usually slows things down.
    Pass ``parallel=True`` and ``max_workers`` to opt in; ``max_workers=None``
    runs every job at once.

    Pass an existing ``cancel`` event to allow an outer UI thread to abort.
    When ``numbered`` is true, filenames are prefixed ``1_``, ``2_``, … in
    selection order.
    """
    if not nodes:
        return [], 0

    export_dir.mkdir(parents=True, exist_ok=True)
    used_paths: set[Path] = set()
    jobs: list[tuple[int, model.Node, Path]] = []
    for index, node in enumerate(nodes):
        if single_output and len(nodes) == 1:
            dest = single_output
        else:
            dest = output_path_for(
                node,
                export_dir,
                source,
                connection,
                used_paths=used_paths,
                sequence=(index + 1) if numbered else None,
            )
        jobs.append((index, node, dest))

    total = len(jobs)
    lock = threading.Lock()
    results: list[export_module.ExportResult | None] = [None] * total
    failures = 0
    if cancel is None:
        cancel = threading.Event()
    cancelled = False

    def reporter(state: ProgressState) -> None:
        if on_progress is None:
            return
        with lock:
            on_progress(state)

    # Seed every slot so the UI can list all objects before workers start.
    if on_progress is not None:
        for index, node, _dest in jobs:
            on_progress(
                {
                    "slot": index,
                    "node": node.name,
                    "node_index": index + 1,
                    "node_total": total,
                    "step": "prepare",
                    "percent": 0.0,
                    "detail": "",
                }
            )

    def run_job(index: int, node: model.Node, dest: Path) -> export_module.ExportResult:
        return _export_one(
            source,
            work_dir,
            node,
            dest,
            closure_mode=closure_mode,
            backward_groups=backward_groups,
            backward_iterations=backward_iterations,
            dry_run=dry_run,
            overwrite=overwrite,
            resume=resume,
            skip_check=skip_check,
            reporter=reporter,
            node_index=index,
            node_total=total,
            cancel=cancel,
        )

    def mark_cancelled_slots() -> None:
        if on_progress is None:
            return
        for index, node, _dest in jobs:
            if results[index] is None:
                on_progress(
                    {
                        "slot": index,
                        "node": node.name,
                        "node_index": index + 1,
                        "node_total": total,
                        "step": "done",
                        "percent": float(0),
                        "detail": "cancelled",
                        "finished": False,
                    }
                )

    if not parallel or total <= 1:
        workers = 1
    elif max_workers is None or max_workers <= 0:
        workers = total
    else:
        workers = min(max_workers, total)

    if workers == 1:
        try:
            for index, node, dest in jobs:
                if cancel.is_set():
                    break
                try:
                    results[index] = run_job(index, node, dest)
                except ExportCancelled:
                    cancelled = True
                    break
                except SystemExit as error:
                    failures += 1
                    log(str(error))
                except Exception as error:  # noqa: BLE001
                    failures += 1
                    log(f"Export failed for {node.name}: {error}")
        except KeyboardInterrupt:
            cancel.set()
            cancelled = True
    else:
        pool = ThreadPoolExecutor(max_workers=workers)
        future_map = {
            pool.submit(run_job, index, node, dest): index
            for index, node, dest in jobs
        }
        try:
            for future in as_completed(future_map):
                index = future_map[future]
                try:
                    results[index] = future.result()
                except ExportCancelled:
                    cancelled = True
                except SystemExit as error:
                    failures += 1
                    log(str(error))
                except Exception as error:  # noqa: BLE001
                    failures += 1
                    node = jobs[index][1]
                    log(f"Export failed for {node.name}: {error}")
                if cancelled:
                    break
        except KeyboardInterrupt:
            cancel.set()
            cancelled = True
        finally:
            cancel.set()
            for future in future_map:
                future.cancel()
            # Do not wait for long-running workers; they exit via cancel_check.
            pool.shutdown(wait=False, cancel_futures=True)

    if cancelled:
        mark_cancelled_slots()
        raise KeyboardInterrupt

    return [r for r in results if r is not None], failures
