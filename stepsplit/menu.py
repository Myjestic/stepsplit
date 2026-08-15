"""Interactive main menu in the same colorful curses style as the tree browser."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import VERSION, model, scan, storage, tui, ui, validate
from . import i18n as i18n_mod
from . import settings as settings_mod
from . import setup as setup_mod
from .util import format_bytes, is_step_file


def run_tree_export(
    screen,
    session: "Session",
    connection,
    nodes: list[model.Node],
) -> bool:
    """Export marked nodes with in-menu progress and hierarchical folders."""
    import threading

    from . import export_batch as batch

    tr = i18n_mod.get_i18n().t
    source = session.source
    work_dir = session.work_dir
    session.output_dir.mkdir(parents=True, exist_ok=True)
    cancel = threading.Event()

    def work(on_progress) -> tuple[bool, str]:
        # Open a fresh DB connection in this worker thread. SQLite connections
        # must not cross threads (the tree browser keeps one on the UI thread).
        export_connection = storage.connect_readonly(work_dir)
        try:
            _results, failures = batch.export_nodes(
                source,
                work_dir,
                export_connection,
                nodes,
                session.output_dir,
                overwrite=session.settings.overwrite_exports,
                on_progress=on_progress,
                parallel=False,
                skip_check=True,
                resume=False,
                backward_iterations=1,
                cancel=cancel,
                numbered=session.settings.numbered_exports,
            )
        finally:
            export_connection.close()
        ok = failures == 0
        return ok, tr("export_done_ok") if ok else tr("export_done_fail")

    return ui.run_export_progress(
        screen, tr("export_progress_title"), len(nodes), work, cancel=cancel
    )


@dataclass
class Session:
    source: Path
    output_dir: Path
    work_dir: Path
    settings: settings_mod.Settings
    project_export: Path
    message: str = ""

    def refresh_paths(self) -> None:
        if self.source.is_file():
            self.work_dir = settings_mod.resolve_work_dir(self.settings, self.source)
            self.output_dir = settings_mod.resolve_export_dir(
                self.settings, self.source, self.project_export
            )


# Kept for entry-point compatibility.
def default_work_dir(source: Path) -> Path:
    return settings_mod.resolve_work_dir(settings_mod.load_settings(), source)


def index_status(source: Path, work_dir: Path, language: str) -> dict:
    """Return a human-readable snapshot of the index on disk."""
    tr = i18n_mod.I18n(language).t
    info = {
        "state": tr("index_missing_short"),
        "entities": 0,
        "products": 0,
        "usages": 0,
        "candidates": 0,
        "offsets": False,
        "detail": tr("index_missing"),
        "ready": False,
        "resumable": False,
    }
    db = storage.structure_db_path(work_dir)
    if not db.exists():
        return info
    try:
        connection = storage.connect_readonly(work_dir)
        meta = storage.read_meta(connection)
        counts = model.counts(connection)
        connection.close()
    except Exception as error:  # noqa: BLE001
        info["state"] = tr("index_bad")
        info["detail"] = str(error)
        return info

    meta_source = meta.get("source")
    if meta_source and source.is_file():
        try:
            if Path(meta_source).resolve() != source.resolve():
                info["state"] = tr("index_mismatch")
                info["detail"] = tr("index_mismatch_detail")
                return info
        except OSError:
            info["state"] = tr("index_mismatch")
            info["detail"] = tr("index_mismatch_detail")
            return info

    state = meta.get("scan_state", "unknown")
    info["entities"] = int(meta.get("scan_entities", 0))
    info["products"] = counts.get("products", 0)
    info["usages"] = counts.get("usages", 0)
    info["offsets"] = model.has_offsets(work_dir)
    cand = storage.candidates_path(work_dir)
    info["candidates"] = cand.stat().st_size // 8 if cand.exists() else 0
    info["build_id"] = meta.get("index_build_id", "")

    def _n(value: int) -> str:
        text = f"{value:,}"
        return text.replace(",", ".") if language == "de" else text

    if state == "complete":
        info["state"] = tr("index_ready")
        info["ready"] = True
        info["detail"] = tr(
            "index_detail_ready",
            entities=_n(info["entities"]),
            products=_n(info["products"]),
            usages=_n(info["usages"]),
        )
        if info["build_id"]:
            info["detail"] += tr("index_detail_build", build_id=info["build_id"])
        if not info["offsets"]:
            info["detail"] += tr("index_detail_no_offsets")
        if info["candidates"] == 0:
            info["detail"] += tr("index_detail_no_candidates")
    elif state == "running":
        offset = int(meta.get("scan_offset", 0))
        size = max(source.stat().st_size, 1) if source.is_file() else 1
        percent = offset / size * 100
        info["state"] = tr("index_broken")
        info["resumable"] = True
        info["detail"] = tr(
            "index_detail_progress",
            percent=percent,
            bytes=format_bytes(offset),
        )
    else:
        info["state"] = state
        info["detail"] = f"scan_state={state!r}"
    return info


def choose_source(screen, session: Session) -> None:
    tr = i18n_mod.get_i18n().t
    path_text = ui.prompt_text(
        screen,
        tr("source_title"),
        tr("source_prompt"),
        str(session.source),
        path_complete=True,
        step_files_only=True,
    )
    if path_text is None:
        session.message = tr("cancelled")
        return
    path = Path(path_text).expanduser()
    if not path.is_file():
        ui.show_lines(screen, tr("error"), [f"{tr('source_missing')}: {path}"])
        return
    if not is_step_file(path):
        ui.show_lines(screen, tr("error"), [tr("source_not_step", name=path.name)])
        return
    session.source = path.resolve()
    session.settings.last_source = str(session.source)
    session.refresh_paths()
    settings_mod.save_settings(session.settings)
    session.message = f"{session.source.name}  →  {session.work_dir}"


def run_index(screen, session: Session, force: bool = False) -> None:
    tr = i18n_mod.get_i18n().t
    source = session.source
    if not source.is_file():
        ui.show_lines(screen, tr("error"), [f"{tr('source_missing')}: {source}"])
        return
    if not is_step_file(source):
        ui.show_lines(screen, tr("error"), [tr("source_not_step", name=source.name)])
        return
    session.refresh_paths()
    work_dir = session.work_dir
    status = index_status(source, work_dir, session.settings.language)
    size = format_bytes(source.stat().st_size)

    def finish_status() -> tuple[bool, str, str]:
        current = index_status(source, work_dir, session.settings.language)
        if current["ready"]:
            return True, tr("index_created"), str(current["detail"])
        return False, tr("index_done_fail"), str(current["detail"])

    if status["ready"] and not force:
        if status["candidates"] == 0:
            if not ui.confirm(
                screen,
                tr("menu_index"),
                tr("index_candidates_hint") + "\n\n" + tr("confirm_ok"),
                default_no=False,
            ):
                return

            def enrich(on_progress) -> None:
                try:
                    scan.enrich_candidates(
                        source, work_dir, force=True, on_progress=on_progress
                    )
                except KeyboardInterrupt:
                    pass
                except SystemExit as error:
                    session.message = str(error)

            ui.run_with_progress(
                screen,
                tr("menu_index"),
                f"{source.name}  ({size})",
                enrich,
                finish=finish_status,
            )
            return
        return

    title = tr("menu_rebuild") if force else tr("menu_index")
    if force:
        question = tr("confirm_rebuild", name=source.name, size=size)
    elif status.get("resumable"):
        title = tr("menu_resume")
        question = tr(
            "confirm_resume",
            name=source.name,
            size=size,
            detail=status["detail"],
        )
    else:
        question = tr("confirm_index", name=source.name, size=size)
    if not ui.confirm(screen, title, question, default_no=force):
        return

    def build(on_progress) -> None:
        try:
            scan.build_index(
                source,
                work_dir,
                with_offsets=True,
                force=force,
                resume=not force,
                on_progress=on_progress,
                quiet=True,
            )
        except KeyboardInterrupt:
            pass
        except SystemExit as error:
            session.message = str(error)

    ui.run_with_progress(
        screen,
        title,
        f"{source.name}  ({size})",
        build,
        finish=finish_status,
    )


def run_browse(screen, session: Session) -> None:
    tr = i18n_mod.get_i18n().t
    source = session.source
    session.refresh_paths()
    work_dir = session.work_dir
    if not source.is_file():
        ui.show_lines(screen, tr("error"), [f"{tr('source_missing')}: {source}"])
        return
    if not is_step_file(source):
        ui.show_lines(screen, tr("error"), [tr("source_not_step", name=source.name)])
        return
    status = index_status(source, work_dir, session.settings.language)
    if not status["ready"]:
        ui.show_lines(
            screen,
            tr("label_index"),
            [f"{status['state']}", status["detail"], "", tr("need_index")],
        )
        return
    if status["usages"] == 0:
        ui.show_lines(screen, tr("error"), [tr("err_no_usages_export")])
        return

    session.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        connection = model.open_structure(source, work_dir)
    except SystemExit as error:
        ui.show_lines(screen, tr("error"), [str(error)])
        return

    report = validate.validate_structure(connection)
    if not report.ok:
        connection.close()
        ui.show_lines(screen, tr("error"), report.render().splitlines())
        return

    def run_export(screen, nodes: list[model.Node]) -> bool:
        return run_tree_export(screen, session, connection, nodes)

    try:
        tree = tui.Tree(connection, source.name)
        if not tree.root.children:
            ui.show_lines(screen, tr("error"), [tr("err_no_roots")])
            return
        browser = tui.Browser(
            tree,
            run_export,
            subtitle=f"{source.name}  →  {session.output_dir}",
            language=session.settings.language,
        )
        browser.run(screen)
        session.message = tr("tree_status_done")
    except SystemExit as error:
        ui.show_lines(screen, tr("error"), [str(error)])
    finally:
        connection.close()


def run_status(screen, session: Session) -> None:
    tr = i18n_mod.get_i18n().t
    source = session.source
    if not source.is_file():
        ui.show_lines(screen, tr("error"), [f"{tr('source_missing')}: {source}"])
        return
    session.refresh_paths()
    status = index_status(source, session.work_dir, session.settings.language)
    yes = tr("label_yes")
    no = tr("label_no")
    panel = ui.HeaderPanel(
        eyebrow=source.name,
        rows=[
            (tr("label_file"), str(source)),
            (tr("label_size"), format_bytes(source.stat().st_size)),
            (tr("label_index"), status["state"], _index_value_color(status)),
            ("", status["detail"]),
            (tr("label_offsets"), yes if status["offsets"] else no),
            (tr("label_work"), str(session.work_dir)),
            (tr("label_export"), str(session.output_dir)),
            (tr("label_settings"), str(settings_mod.settings_path())),
        ],
    )
    findings: list[tuple[str, str]] = []
    result_ok: bool | None = None
    result_text = ""
    if status["ready"]:
        try:
            connection = model.open_structure(source, session.work_dir)
            report = validate.validate_structure(connection)
            connection.close()
            findings = list(report.findings)
            result_ok = report.ok
            result_text = tr("val_result_ok") if report.ok else tr("val_result_bad")
        except SystemExit as error:
            findings = [("error", str(error))]
            result_ok = False
            result_text = tr("val_result_bad")
    ui.show_status(
        screen,
        tr("menu_status"),
        panel,
        findings,
        result_ok,
        result_text,
    )


def _main_items(session: Session) -> list[ui.MenuItem]:
    tr = i18n_mod.get_i18n().t
    status = (
        index_status(session.source, session.work_dir, session.settings.language)
        if session.source.is_file()
        else {"ready": False, "resumable": False, "state": "-"}
    )
    ready = bool(status.get("ready"))
    resumable = bool(status.get("resumable"))
    if ready:
        index_item = ui.MenuItem("rebuild", tr("menu_rebuild"), tr("menu_rebuild_hint"))
    elif resumable:
        index_item = ui.MenuItem("index", tr("menu_resume"), tr("menu_resume_hint"))
    else:
        index_item = ui.MenuItem("index", tr("menu_index"), tr("menu_index_hint"))
    return [
        ui.MenuItem("source", tr("menu_source"), tr("menu_source_hint")),
        index_item,
        ui.MenuItem(
            "browse",
            tr("menu_browse"),
            tr("menu_browse_hint"),
            enabled=ready,
        ),
        ui.MenuItem("status", tr("menu_status"), str(status.get("state", ""))),
        ui.MenuItem("_gap1", "", separator=True),
        ui.MenuItem("_gap2", "", separator=True),
        ui.MenuItem("settings", tr("menu_settings"), tr("menu_settings_hint")),
        ui.MenuItem("_gap3", "", separator=True),
        ui.MenuItem("quit", tr("menu_quit")),
    ]


def _index_value_color(status: dict) -> int:
    if status.get("ready"):
        return ui.C_OK
    state = str(status.get("state", ""))
    tr = i18n_mod.get_i18n().t
    if state in {tr("index_broken"), tr("index_bad"), tr("index_mismatch")}:
        return ui.C_WARN
    if state in {tr("index_missing_short"), "-"}:
        return ui.C_ACCENT
    return ui.C_MUTED


def _header_panel(session: Session) -> ui.HeaderPanel:
    tr = i18n_mod.get_i18n().t
    exists = session.source.is_file()
    size = format_bytes(session.source.stat().st_size) if exists else "-"
    status = (
        index_status(session.source, session.work_dir, session.settings.language)
        if exists
        else {"state": "-", "detail": tr("source_missing"), "ready": False}
    )
    source_name = session.source.name if exists else str(session.source)

    def short(path: Path) -> str:
        text = str(path)
        home = str(Path.home())
        if text.startswith(home):
            return "~" + text[len(home) :]
        return text

    index_text = f"{status['state']}  ·  {status['detail']}"
    return ui.HeaderPanel(
        eyebrow=f"v{VERSION}  ·  {session.settings.language.upper()}",
        rows=[
            (tr("label_file"), source_name),
            (tr("label_size"), size),
            (tr("label_index"), index_text, _index_value_color(status)),
            (tr("label_work"), short(session.work_dir)),
            (tr("label_export"), short(session.output_dir)),
        ],
        note=session.message,
    )


def _app(screen, session: Session) -> int:
    ui.THEME.color = session.settings.color
    ui.THEME.init(screen)
    if not session.settings.setup_complete:
        session.settings = setup_mod.run_wizard(screen, session.settings)
        session.refresh_paths()

    tr = i18n_mod.get_i18n().t
    cursor = 0
    while True:
        items = _main_items(session)
        if not session.message:
            ready = any(item.key == "browse" and item.enabled for item in items)
            preferred = "browse" if ready else "index"
            for index, item in enumerate(items):
                if item.key == preferred and item.enabled:
                    cursor = index
                    break
            else:
                for index, item in enumerate(items):
                    if item.key in {"index", "rebuild"} and item.enabled:
                        cursor = index
                        break
        choice = ui.list_menu(
            screen,
            tr("app_title"),
            items,
            panel=_header_panel(session),
            cursor=cursor,
            status=tr("nav_footer_main"),
        )
        session.message = ""
        if choice is None or choice == "quit":
            settings_mod.save_settings(session.settings)
            return 0
        for index, item in enumerate(items):
            if item.key == choice:
                cursor = index
                break
        if choice == "source":
            choose_source(screen, session)
        elif choice == "index":
            run_index(screen, session, force=False)
        elif choice == "browse":
            run_browse(screen, session)
        elif choice == "status":
            run_status(screen, session)
        elif choice == "settings":
            session.settings = setup_mod.edit_settings(screen, session.settings)
            ui.THEME.color = session.settings.color
            session.refresh_paths()
        elif choice == "rebuild":
            run_index(screen, session, force=True)


def run_menu(
    source: Path,
    output_dir: Path,
    work_dir: Path | None = None,
) -> int:
    settings = settings_mod.load_settings()
    i18n_mod.set_language(settings.language)
    ui.THEME.color = settings.color

    if settings.last_source:
        candidate = Path(settings.last_source).expanduser()
        if candidate.is_file():
            source = candidate
    resolved_source = source.resolve() if source.exists() else source
    session = Session(
        source=resolved_source,
        output_dir=output_dir,
        work_dir=(
            settings_mod.resolve_work_dir(settings, resolved_source)
            if resolved_source.exists()
            else Path.home() / ".cache" / "stepsplit" / "unset"
        ),
        settings=settings,
        project_export=output_dir,
    )
    # Always derive the index folder from the active source. A default work_dir
    # from the entry script (tied to DEFAULT_SOURCE) must not stick after
    # last_source points at a different file.
    if resolved_source.exists():
        session.refresh_paths()
    elif work_dir is not None:
        session.work_dir = work_dir
    return ui.run(lambda screen: _app(screen, session))
