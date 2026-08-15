"""First-run setup wizard and settings editor."""

from __future__ import annotations

from pathlib import Path

from . import i18n as i18n_mod
from . import settings as settings_mod
from . import ui


def run_wizard(screen, settings: settings_mod.Settings) -> settings_mod.Settings:
    """Ask for language, export dir, work dir and colors; persist the result."""
    tr = i18n_mod.get_i18n().t

    # Language first; bilingual labels until chosen.
    lang = ui.list_menu(
        screen,
        "StepSplit",
        [
            ui.MenuItem("de", "Deutsch", "German"),
            ui.MenuItem("en", "English", "Englisch"),
        ],
        subtitle_lines=[
            tr("wizard_welcome") if settings.language else "Welcome / Willkommen",
            "Choose language / Sprache wählen",
        ],
        status="↑↓  Enter  ·  Esc keeps current",
        cursor=0 if settings.language != "en" else 1,
    )
    if lang in {"de", "en"}:
        settings.language = lang
        i18n_mod.set_language(lang)
    tr = i18n_mod.get_i18n().t

    export = ui.list_menu(
        screen,
        tr("wizard_export"),
        [
            ui.MenuItem("beside_source", tr("wizard_export_beside")),
            ui.MenuItem("project_export", tr("wizard_export_project")),
            ui.MenuItem("custom", tr("wizard_export_custom")),
        ],
        cursor={"beside_source": 0, "project_export": 1, "custom": 2}.get(
            settings.export_mode, 0
        ),
    )
    if export:
        settings.export_mode = export
    if settings.export_mode == "custom":
        path = ui.prompt_text(
            screen,
            tr("wizard_export"),
            tr("wizard_export_path"),
            settings.export_dir or str(Path.home() / "step-export"),
            path_complete=True,
        )
        if path is not None:
            settings.export_dir = path

    work = ui.list_menu(
        screen,
        tr("wizard_work"),
        [
            ui.MenuItem("cache", tr("wizard_work_cache")),
            ui.MenuItem("beside_source", tr("wizard_work_beside")),
            ui.MenuItem("custom", tr("wizard_work_custom")),
        ],
        cursor={"cache": 0, "beside_source": 1, "custom": 2}.get(settings.work_mode, 0),
    )
    if work:
        settings.work_mode = work
    if settings.work_mode == "custom":
        path = ui.prompt_text(
            screen,
            tr("wizard_work"),
            tr("wizard_work_path"),
            settings.work_dir or str(Path.home() / "step-index"),
            path_complete=True,
        )
        if path is not None:
            settings.work_dir = path

    color = ui.list_menu(
        screen,
        tr("wizard_color"),
        [
            ui.MenuItem("on", tr("wizard_color_on")),
            ui.MenuItem("off", tr("wizard_color_off")),
        ],
        cursor=0 if settings.color else 1,
    )
    if color == "on":
        settings.color = True
        ui.THEME.color = True
    elif color == "off":
        settings.color = False
        ui.THEME.color = False

    settings.setup_complete = True
    settings_mod.save_settings(settings)
    ui.show_lines(screen, tr("settings_title"), [tr("wizard_done")])
    return settings


def edit_settings(screen, settings: settings_mod.Settings) -> settings_mod.Settings:
    tr = i18n_mod.get_i18n().t
    while True:
        color_label = tr("color_on") if settings.color else tr("color_off")
        numbered_label = (
            tr("settings_numbered_on")
            if settings.numbered_exports
            else tr("settings_numbered_off")
        )
        export_label = {
            "beside_source": tr("wizard_export_beside"),
            "project_export": tr("wizard_export_project"),
            "custom": tr("wizard_export_custom"),
        }.get(settings.export_mode, settings.export_mode)
        work_label = {
            "cache": tr("wizard_work_cache"),
            "beside_source": tr("wizard_work_beside"),
            "custom": tr("wizard_work_custom"),
        }.get(settings.work_mode, settings.work_mode)
        choice = ui.list_menu(
            screen,
            tr("settings_title"),
            [
                ui.MenuItem("language", tr("settings_language"), settings.language.upper()),
                ui.MenuItem("export", tr("settings_export"), export_label),
                ui.MenuItem("work", tr("settings_work"), work_label),
                ui.MenuItem("numbered", tr("settings_numbered"), numbered_label),
                ui.MenuItem("color", tr("settings_color"), color_label),
                ui.MenuItem("wizard", tr("settings_rerun")),
                ui.MenuItem("_gap", "", separator=True),
                ui.MenuItem("back", tr("settings_back")),
            ],
            hint_mode="aligned",
        )
        if choice in {None, "back"}:
            settings_mod.save_settings(settings)
            return settings
        if choice == "language":
            lang = ui.list_menu(
                screen,
                tr("wizard_language"),
                [
                    ui.MenuItem("de", tr("wizard_lang_de")),
                    ui.MenuItem("en", tr("wizard_lang_en")),
                ],
                cursor=0 if settings.language != "en" else 1,
            )
            if lang in {"de", "en"}:
                settings.language = lang
                i18n_mod.set_language(lang)
                tr = i18n_mod.get_i18n().t
        elif choice == "export":
            export = ui.list_menu(
                screen,
                tr("wizard_export"),
                [
                    ui.MenuItem("beside_source", tr("wizard_export_beside")),
                    ui.MenuItem("project_export", tr("wizard_export_project")),
                    ui.MenuItem("custom", tr("wizard_export_custom")),
                ],
            )
            if export:
                settings.export_mode = export
            if settings.export_mode == "custom":
                path = ui.prompt_text(
                    screen,
                    tr("wizard_export"),
                    tr("wizard_export_path"),
                    settings.export_dir or str(Path.home() / "step-export"),
                    path_complete=True,
                )
                if path is not None:
                    settings.export_dir = path
        elif choice == "work":
            work = ui.list_menu(
                screen,
                tr("wizard_work"),
                [
                    ui.MenuItem("cache", tr("wizard_work_cache")),
                    ui.MenuItem("beside_source", tr("wizard_work_beside")),
                    ui.MenuItem("custom", tr("wizard_work_custom")),
                ],
            )
            if work:
                settings.work_mode = work
            if settings.work_mode == "custom":
                path = ui.prompt_text(
                    screen,
                    tr("wizard_work"),
                    tr("wizard_work_path"),
                    settings.work_dir or str(Path.home() / "step-index"),
                    path_complete=True,
                )
                if path is not None:
                    settings.work_dir = path
        elif choice == "numbered":
            settings.numbered_exports = not settings.numbered_exports
        elif choice == "color":
            settings.color = not settings.color
            ui.THEME.color = settings.color
        elif choice == "wizard":
            settings = run_wizard(screen, settings)
            tr = i18n_mod.get_i18n().t
