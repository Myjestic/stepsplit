"""Command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import VERSION, export as export_module, i18n as i18n_mod, model, scan, storage, tui, validate
from . import menu as menu_module
from . import settings as settings_mod
from .util import format_bytes, log, safe_filename

DEFAULT_CACHE = Path.home() / ".cache" / "stepsplit"


def default_work_dir(source: Path) -> Path:
    return menu_module.default_work_dir(source)


def resolve_source(path: Path) -> Path:
    source = path.expanduser()
    if not source.is_file():
        raise SystemExit(f"Source STEP file not found: {source}")
    from .util import is_step_file

    if not is_step_file(source):
        raise SystemExit(
            f"Not a STEP file (expected .stp / .step): {source.name}"
        )
    return source


def ensure_index(source: Path, work_dir: Path, structure_only: bool) -> None:
    """Build the index when it is missing or incomplete."""
    try:
        connection = storage.connect(work_dir)
    except FileNotFoundError:
        connection = None
    state = None
    if connection is not None:
        state = storage.read_meta(connection).get("scan_state")
        connection.close()
    if state == "complete":
        return
    log(f"No complete index in {work_dir}; scanning {source.name} ({format_bytes(source.stat().st_size)}).")
    scan.build_index(source, work_dir, with_offsets=not structure_only)


def command_index(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    scan.build_index(
        source,
        work_dir,
        with_offsets=not args.structure_only,
        force=args.force,
        resume=not args.no_resume,
    )
    log(f"Work directory: {work_dir}")
    return 0


def command_enrich(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    scan.enrich_candidates(source, work_dir, force=args.force)
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    connection = model.open_structure(source, work_dir, require_complete=False)
    candidate_path = storage.candidates_path(work_dir)
    payload = {
        "version": VERSION,
        "source": str(source),
        "work_dir": str(work_dir),
        "offset_index": model.has_offsets(work_dir),
        "backward_candidates": (
            candidate_path.stat().st_size // 8 if candidate_path.exists() else 0
        ),
        "metadata": storage.read_meta(connection),
        "counts": model.counts(connection),
    }
    connection.close()
    print(json.dumps(payload, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    connection = model.open_structure(source, work_dir)
    report = validate.validate_structure(connection)
    print(report.render())
    if args.samples:
        print("\nUsage records as stored in the source file:")
        for row, raw in validate.sample_usages(connection, source, work_dir, args.samples):
            usage_id, parent, child, usage_type, mode = row
            print(f"\n  #{usage_id} {usage_type} parent=#{parent} child=#{child} ({mode})")
            if raw:
                for line in raw.decode("latin-1").splitlines():
                    print(f"    {line}")
    connection.close()
    return 0 if report.ok else 2


def command_tree(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    connection = model.open_structure(source, work_dir)

    if args.select:
        roots = [node.pd_id for selector in args.select for node in model.resolve_selector(connection, selector)]
    else:
        roots = model.root_pds(connection)

    if args.json:
        payload = [_tree_json(connection, root, args.max_depth) for root in roots]
        text = json.dumps(payload, indent=2)
    else:
        lines: list[str] = []
        for root in roots:
            for depth, node in model.iter_tree(connection, root, args.max_depth):
                marker = " [cycle]" if node.cycle else ""
                children = f" ({node.child_count})" if node.child_count else ""
                lines.append(
                    f"{'  ' * depth}{node.label} [PD #{node.pd_id}]"
                    f"{children}{marker}{' [Körper]' if node.is_body else ''}"
                )
        text = "\n".join(lines)
    connection.close()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        log(f"Tree written to {args.output}")
    else:
        print(text)
    return 0


def _tree_json(connection, root_pd: int, max_depth: int | None) -> dict:
    root_entry: dict | None = None
    stack: list[dict] = []
    for depth, node in model.iter_tree(connection, root_pd, max_depth):
        entry = {
            "pd_id": node.pd_id,
            "name": node.name,
            "usage_id": node.usage_id,
            "designator": node.designator,
            "child_count": node.child_count,
            "cycle": node.cycle,
            "is_body": node.is_body,
            "children": [],
        }
        del stack[depth:]
        if stack:
            stack[-1]["children"].append(entry)
        else:
            root_entry = entry
        stack.append(entry)
    return root_entry or {}


def _backward_groups(value: str) -> tuple[str, ...]:
    if value in ("none", ""):
        return ()
    if value == "all":
        return tuple(export_module.BACKWARD_GROUPS)
    groups = tuple(part.strip() for part in value.split(",") if part.strip())
    for group in groups:
        if group not in export_module.BACKWARD_GROUPS:
            raise SystemExit(
                f"Unknown backward group {group!r}. Known: "
                + ", ".join(export_module.BACKWARD_GROUPS)
            )
    return groups


def _export_nodes(
    source: Path,
    work_dir: Path,
    connection,
    nodes: list[model.Node],
    args: argparse.Namespace,
) -> int:
    if not nodes:
        log("Nothing selected; no STEP file written.")
        return 1

    report = validate.validate_structure(connection)
    if not report.ok:
        log(report.render())
        log("\nRefusing to export while the assembly structure is invalid.")
        return 2

    from . import export_batch as batch

    backward_groups = _backward_groups(args.backward)
    _results, failures = batch.export_nodes(
        source,
        work_dir,
        connection,
        nodes,
        args.output_dir,
        closure_mode=args.closure_mode,
        backward_groups=backward_groups,
        backward_iterations=args.backward_iterations,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        skip_check=args.skip_check,
        parallel=False,
        single_output=args.output if args.output and len(nodes) == 1 else None,
    )
    for result in _results:
        log(export_module.describe(result))
    return 1 if failures else 0


def command_export(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    connection = model.open_structure(source, work_dir)
    nodes: list[model.Node] = []
    for selector in args.select:
        nodes.extend(model.resolve_selector(connection, selector))
    status = _export_nodes(source, work_dir, connection, nodes, args)
    connection.close()
    return status


def command_browse(args: argparse.Namespace) -> int:
    source = resolve_source(args.source)
    work_dir = args.work_dir or default_work_dir(source)
    if args.auto_index:
        ensure_index(source, work_dir, args.structure_only)
    connection = model.open_structure(source, work_dir)

    report = validate.validate_structure(connection)
    if not report.ok:
        print(report.render())
        connection.close()
        return 2

    def run_export(screen, nodes: list[model.Node]) -> bool:
        return _export_nodes(source, work_dir, connection, nodes, args) == 0

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit(
            "The structure browser needs an interactive terminal. "
            "Use the 'tree' and 'export' commands instead."
        )
    language = args.language or settings_mod.load_settings().language
    i18n_mod.set_language(language)
    tui.browse(
        connection,
        title=source.name,
        export=run_export,
        subtitle=f"{source.name} → {args.output_dir}",
        language=language,
    )
    connection.close()
    return 0


def command_check(args: argparse.Namespace) -> int:
    report = validate.validate_step_file(resolve_source(args.file))
    print(report.render())
    return 0 if report.ok else 2


def _add_common(parser: argparse.ArgumentParser, default_source: Path | None) -> None:
    parser.add_argument(
        "source",
        nargs="?" if default_source else None,
        default=default_source,
        type=Path,
        help="STEP file to read (never modified)",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="directory for the index; defaults to a folder under ~/.cache",
    )


def _add_export_options(parser: argparse.ArgumentParser, default_output_dir: Path) -> None:
    parser.add_argument("--output", type=Path, help="output file for a single selection")
    parser.add_argument(
        "--output-dir", type=Path, default=default_output_dir, help="directory for exports"
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing output files")
    parser.add_argument("--dry-run", action="store_true", help="estimate size without writing")
    parser.add_argument(
        "--closure-mode",
        choices=("auto", "random", "passes"),
        default="auto",
        help="random uses the offset index, passes re-reads the file instead",
    )
    parser.add_argument(
        "--backward",
        default=",".join(export_module.DEFAULT_BACKWARD_GROUPS),
        help="backward reference groups to include: none, all or a comma separated list of "
        + ", ".join(export_module.BACKWARD_GROUPS),
    )
    parser.add_argument("--backward-iterations", type=int, default=3)
    parser.add_argument(
        "--skip-check", action="store_true", help="do not validate the written STEP file"
    )


def build_parser(default_source: Path | None, default_output_dir: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stepsplit",
        description="Browse and split very large STEP assemblies without loading geometry.",
    )
    parser.add_argument("--version", action="version", version=VERSION)
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="build the disk-backed indexes")
    _add_common(index_parser, default_source)
    index_parser.add_argument(
        "--structure-only",
        action="store_true",
        help="skip the byte offset index (smaller, but export must use --closure-mode passes)",
    )
    index_parser.add_argument("--force", action="store_true", help="rebuild from scratch")
    index_parser.add_argument("--no-resume", action="store_true")
    index_parser.set_defaults(func=command_index)

    enrich_parser = subparsers.add_parser(
        "enrich",
        help="build the backward-candidate list for an existing index (needed once for fast export)",
    )
    _add_common(enrich_parser, default_source)
    enrich_parser.add_argument("--force", action="store_true")
    enrich_parser.set_defaults(func=command_enrich)

    inspect_parser = subparsers.add_parser("inspect", help="print index statistics as JSON")
    _add_common(inspect_parser, default_source)
    inspect_parser.set_defaults(func=command_inspect)

    validate_parser = subparsers.add_parser(
        "validate", help="check the indexed assembly relationships"
    )
    _add_common(validate_parser, default_source)
    validate_parser.add_argument(
        "--samples", type=int, default=0, help="also print N raw usage records"
    )
    validate_parser.set_defaults(func=command_validate)

    tree_parser = subparsers.add_parser("tree", help="print the assembly tree")
    _add_common(tree_parser, default_source)
    tree_parser.add_argument(
        "--select", action="append", default=[], help="product name, '#id' or 'pd:id'"
    )
    tree_parser.add_argument("--max-depth", type=int)
    tree_parser.add_argument("--json", action="store_true")
    tree_parser.add_argument("--output", type=Path)
    tree_parser.set_defaults(func=command_tree)

    browse_parser = subparsers.add_parser(
        "browse", help="interactive tree with collapsible nodes and export"
    )
    _add_common(browse_parser, default_source)
    _add_export_options(browse_parser, default_output_dir)
    browse_parser.add_argument(
        "--language",
        choices=("de", "en"),
        help="UI language (default: from ~/.config/stepsplit/settings.json or de)",
    )
    browse_parser.add_argument(
        "--no-auto-index",
        dest="auto_index",
        action="store_false",
        help="fail instead of indexing when no index exists",
    )
    browse_parser.add_argument("--structure-only", action="store_true")
    browse_parser.set_defaults(func=command_browse)

    export_parser = subparsers.add_parser("export", help="export selected subtrees as STEP files")
    _add_common(export_parser, default_source)
    export_parser.add_argument(
        "--select",
        action="append",
        required=True,
        help="product name, '#id' or 'pd:id'; repeat for several exports",
    )
    _add_export_options(export_parser, default_output_dir)
    export_parser.set_defaults(func=command_export)

    check_parser = subparsers.add_parser(
        "check", help="verify that a STEP file has no missing references"
    )
    check_parser.add_argument("file", type=Path)
    check_parser.set_defaults(func=command_check)

    return parser


def main(
    argv: list[str] | None = None,
    default_source: Path | None = None,
    default_output_dir: Path = Path("export"),
    default_work_dir: Path | None = None,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # No arguments → interactive menu (index, tree, export).
    try:
        if not argv:
            if default_source is None:
                build_parser(default_source, default_output_dir).print_help()
                return 1
            return menu_module.run_menu(default_source, default_output_dir, default_work_dir)

        if argv and argv[0] == "menu":
            source = default_source
            work_dir = default_work_dir
            rest = argv[1:]
            if rest and not rest[0].startswith("-"):
                source = Path(rest[0])
                rest = rest[1:]
            if "--work-dir" in rest:
                idx = rest.index("--work-dir")
                work_dir = Path(rest[idx + 1])
            return menu_module.run_menu(
                source or Path("."),
                default_output_dir,
                work_dir,
            )

        parser = build_parser(default_source, default_output_dir)
        args = parser.parse_args(argv)
        if not getattr(args, "command", None):
            parser.print_help()
            return 1
        return args.func(args)
    except KeyboardInterrupt:
        log("\nInterrupted.")
        return 130
