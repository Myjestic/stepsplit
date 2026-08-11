"""German / English UI strings."""

from __future__ import annotations

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    "app_title": {"de": "StepSplit", "en": "StepSplit"},
    "nav_footer": {
        "de": "↑↓ bewegen   Enter wählen   q zurück",
        "en": "↑↓ move   Enter select   q back",
    },
    "nav_footer_main": {
        "de": "↑↓ bewegen   Enter öffnen   q beenden",
        "en": "↑↓ move   Enter open   q quit",
    },
    "confirm_footer": {
        "de": "↑↓ wählen   Enter bestätigen   q abbrechen",
        "en": "↑↓ choose   Enter confirm   q cancel",
    },
    "prompt_footer": {
        "de": "Enter übernehmen   Esc abbrechen",
        "en": "Enter accept   Esc cancel",
    },
    "prompt_footer_path": {
        "de": "Enter übernehmen   Tab vervollständigen / auflisten   Esc abbrechen",
        "en": "Enter accept   Tab complete / list   Esc cancel",
    },
    "prompt_no_matches": {
        "de": "(keine Treffer)",
        "en": "(no matches)",
    },
    "back_footer": {"de": "Enter / q zurück", "en": "Enter / q back"},
    "yes": {"de": "Ja", "en": "Yes"},
    "no": {"de": "Nein", "en": "No"},
    "yes_hint": {"de": "ausführen", "en": "continue"},
    "no_hint": {"de": "abbrechen", "en": "cancel"},
    "menu_source": {"de": "Quelldatei wählen", "en": "Choose source file"},
    "menu_source_hint": {
        "de": "STEP-Datei und Index-Ordner",
        "en": "STEP file and index folder",
    },
    "menu_index": {"de": "Index einlesen", "en": "Build index"},
    "menu_index_hint": {
        "de": "Struktur scannen / fortsetzen",
        "en": "Scan structure / resume",
    },
    "menu_resume": {"de": "Index fortsetzen", "en": "Resume index"},
    "menu_resume_hint": {
        "de": "unterbrochenen Aufbau fortsetzen",
        "en": "continue the interrupted build",
    },
    "menu_browse": {"de": "Strukturbaum öffnen", "en": "Open structure tree"},
    "menu_browse_hint": {
        "de": "Knoten markieren und exportieren",
        "en": "Mark nodes and export",
    },
    "menu_status": {"de": "Status / Prüfung", "en": "Status / validate"},
    "menu_settings": {"de": "Einstellungen", "en": "Settings"},
    "menu_settings_hint": {
        "de": "Sprache, Export, Farben…",
        "en": "Language, export, colors…",
    },
    "menu_rebuild": {"de": "Index neu aufbauen", "en": "Rebuild index"},
    "menu_rebuild_hint": {
        "de": "löscht den bisherigen Index",
        "en": "deletes the current index",
    },
    "menu_quit": {"de": "Beenden", "en": "Quit"},
    "label_file": {"de": "Datei", "en": "File"},
    "label_size": {"de": "Größe", "en": "Size"},
    "label_index": {"de": "Index", "en": "Index"},
    "label_work": {"de": "Index-Ordner", "en": "Index folder"},
    "label_export": {"de": "Export", "en": "Export"},
    "label_offsets": {"de": "Direktzugriff", "en": "Random access"},
    "label_settings": {"de": "Config", "en": "Settings"},
    "label_yes": {"de": "ja", "en": "yes"},
    "label_no": {"de": "nein", "en": "no"},
    "confirm_ok": {"de": "Fortfahren?", "en": "Continue?"},
    "confirm_index": {
        "de": "{name}  ({size})\n\nIndex jetzt einlesen?",
        "en": "{name}  ({size})\n\nBuild the index now?",
    },
    "confirm_rebuild": {
        "de": (
            "{name}  ({size})\n\n"
            "Index wirklich neu erzeugen?\n"
            "Je nach Dateigröße kann das länger dauern."
        ),
        "en": (
            "{name}  ({size})\n\n"
            "Really rebuild the index?\n"
            "This can take a while depending on file size."
        ),
    },
    "confirm_resume": {
        "de": (
            "{name}  ({size})\n"
            "{detail}\n\n"
            "Unterbrochenen Index fortsetzen?"
        ),
        "en": (
            "{name}  ({size})\n"
            "{detail}\n\n"
            "Resume the interrupted index?"
        ),
    },
    "index_done_title": {"de": "Index", "en": "Index"},
    "index_done_ok": {"de": "fertig", "en": "ready"},
    "index_created": {
        "de": "Index fertig erstellt",
        "en": "Index built successfully",
    },
    "index_done_fail": {"de": "fehlgeschlagen / unterbrochen", "en": "failed / interrupted"},
    "press_key": {
        "de": "Taste drücken → zurück zum Hauptmenü",
        "en": "Press a key → back to main menu",
    },
    "progress_footer": {
        "de": "↑↓ / Mausrad scrollen   Ctrl+C unterbricht",
        "en": "↑↓ / mouse wheel scroll   Ctrl+C interrupts",
    },
    "progress_done_footer": {
        "de": "↑↓ scrollen   Enter → zurück",
        "en": "↑↓ scroll   Enter → back",
    },
    "scan_progress_label": {
        "de": "Index wird gelesen",
        "en": "Reading index",
    },
    "scan_progress_detail": {
        "de": "{entities} Entitäten · {usages} Baugruppen-Links",
        "en": "{entities} entities · {usages} assembly links",
    },
    "scan_progress_finish": {
        "de": "{entities} Entitäten",
        "en": "{entities} entities",
    },
    "scan_done_log": {
        "de": "Index fertig in {seconds:.1f}s: {entities} Entitäten, höchste ID #{max_id}",
        "en": "Index ready in {seconds:.1f}s: {entities} entities, highest id #{max_id}",
    },
    "scan_enrich_label": {
        "de": "Export-Hilfsliste erzeugen",
        "en": "Building export helper list",
    },
    "scan_enrich_detail": {
        "de": "{count} Einträge · {scanned} Records",
        "en": "{count} entries · {scanned} records",
    },
    "scan_enrich_finish": {
        "de": "{count} Einträge",
        "en": "{count} entries",
    },
    "index_missing": {
        "de": "Noch kein Index. Zuerst „Index einlesen“ wählen.",
        "en": "No index yet. Choose “Build index” first.",
    },
    "index_ready": {"de": "fertig", "en": "ready"},
    "index_missing_short": {"de": "fehlt", "en": "missing"},
    "index_broken": {"de": "unterbrochen", "en": "interrupted"},
    "index_bad": {"de": "fehlerhaft", "en": "broken"},
    "index_mismatch": {
        "de": "passt nicht zur Datei",
        "en": "does not match file",
    },
    "index_mismatch_detail": {
        "de": "Index gehört zu einer anderen Quelldatei — neu einlesen.",
        "en": "Index belongs to a different source file — rebuild it.",
    },
    "index_detail_ready": {
        "de": "{entities} Entitäten · {products} Bauteile · {usages} Baugruppen-Links",
        "en": "{entities} entities · {products} parts · {usages} assembly links",
    },
    "index_detail_build": {
        "de": " · Stand {build_id}",
        "en": " · build {build_id}",
    },
    "index_detail_no_offsets": {
        "de": " — kein Direktzugriff-Index",
        "en": " — no random-access index",
    },
    "index_detail_no_candidates": {
        "de": " — Zusatzliste für Export fehlt",
        "en": " — export helper list missing",
    },
    "index_detail_progress": {
        "de": "{percent:.1f}% ({bytes})",
        "en": "{percent:.1f}% ({bytes})",
    },
    "index_candidates_hint": {
        "de": "Zusatzliste für Export fehlt — ein weiterer Durchlauf kann sie erzeugen.",
        "en": "Export helper list missing — one extra pass can build it.",
    },
    "index_readonly_hint": {
        "de": "Quelle bleibt unverändert. Fortschritt folgt. Ctrl+C unterbricht — später fortsetzbar.",
        "en": "Read-only source. Progress follows. Ctrl+C resumes later.",
    },
    "status_section_check": {"de": "Prüfung", "en": "Checks"},
    "status_no_check": {
        "de": "Keine Prüfung möglich — Index fehlt oder ist unvollständig.",
        "en": "No check possible — index missing or incomplete.",
    },
    "sev_ok": {"de": "OK", "en": "OK"},
    "sev_warn": {"de": "WARN", "en": "WARN"},
    "sev_fail": {"de": "FEHLER", "en": "FAIL"},
    "val_result_ok": {
        "de": "Ergebnis: nutzbar für Export",
        "en": "Result: usable for export",
    },
    "val_result_bad": {
        "de": "Ergebnis: NICHT nutzbar für Export",
        "en": "Result: NOT usable for export",
    },
    "val_no_products": {
        "de": "Keine Bauteile (PRODUCT) indexiert.",
        "en": "No parts (PRODUCT) were indexed.",
    },
    "val_no_product_definitions": {
        "de": "Keine Produktdefinitionen indexiert.",
        "en": "No product_definitions were indexed.",
    },
    "val_n_products": {
        "de": "{n} Bauteile (PRODUCT) indexiert.",
        "en": "{n} parts (PRODUCT) indexed.",
    },
    "val_n_product_definitions": {
        "de": "{n} Produktdefinitionen indexiert.",
        "en": "{n} product definitions indexed.",
    },
    "val_no_usages": {
        "de": "Keine Baugruppen-Verknüpfungen indexiert. Unbekannter Usage-Typ — vor Export Parser anpassen.",
        "en": "No assembly usages were indexed. Unrecognised usage entity — adapt the parser before export.",
    },
    "val_n_usages": {
        "de": "{n} Baugruppen-Verknüpfungen indexiert.",
        "en": "{n} assembly usages indexed.",
    },
    "val_fallback_usages": {
        "de": "{n} Verknüpfungen aus nachgestellten Referenzen gelesen statt positional — Stichprobe prüfen.",
        "en": "{n} usages parsed from trailing references instead of positional args — verify a sample.",
    },
    "val_dangling_usages": {
        "de": "{parents} Verknüpfungen zeigen auf unbekannten Parent, {children} auf unbekanntes Child.",
        "en": "{parents} usages point to an unknown parent and {children} to an unknown child.",
    },
    "val_usages_ok": {
        "de": "Jede Verknüpfung verbindet zwei bekannte Produktdefinitionen.",
        "en": "Every usage links two known product definitions.",
    },
    "val_unnamed_pds": {
        "de": "{n} Produktdefinitionen lassen sich keinem Produktnamen zuordnen.",
        "en": "{n} product definitions cannot be resolved to a product name.",
    },
    "val_names_ok": {
        "de": "Jede Produktdefinition hat einen Produktnamen.",
        "en": "Every product definition resolves to a product name.",
    },
    "val_without_shape": {
        "de": "{n} Produktdefinitionen ohne PRODUCT_DEFINITION_SHAPE — Struktur ohne Geometrie.",
        "en": "{n} product definitions have no PRODUCT_DEFINITION_SHAPE — structure without geometry.",
    },
    "val_shapes_ok": {
        "de": "Jede Produktdefinition hat eine Shape.",
        "en": "Every product definition has a shape.",
    },
    "val_no_roots": {
        "de": "Keine Wurzel-Produktdefinition — Graph ist zyklisch.",
        "en": "No root product definition; the assembly graph is cyclic.",
    },
    "val_roots": {
        "de": "{n} Wurzelknoten: {preview}",
        "en": "{n} root node(s): {preview}",
    },
    "val_cycle_skipped": {
        "de": "Zyklusprüfung übersprungen: {n} Verknüpfungen über dem Limit von {limit}.",
        "en": "Cycle check skipped: {n} usages exceed the {limit} edge budget.",
    },
    "val_cycles": {
        "de": "{n} Produktdefinition(en) liegen auf einem Zyklus: {preview}",
        "en": "{n} product definition(s) sit on a cycle: {preview}",
    },
    "val_acyclic": {
        "de": "Der Baugruppen-Graph ist azyklisch.",
        "en": "The assembly graph is acyclic.",
    },
    "val_ambiguous_names": {
        "de": "{n} Produktnamen gehören zu mehr als einer Definition — per „#id“ auswählen.",
        "en": "{n} product names map to more than one product definition; select by '#id'.",
    },
    "err_no_usages_export": {
        "de": "Keine Baugruppen-Verknüpfungen — Export unsicher.",
        "en": "No assembly usages — export unsafe.",
    },
    "err_no_roots": {
        "de": "Keine Wurzelknoten.",
        "en": "No root nodes.",
    },
    "aborted": {"de": "Abgebrochen.", "en": "Aborted."},
    "ok_short": {"de": "OK", "en": "OK"},
    "wizard_welcome": {
        "de": "Willkommen — Ersteinrichtung",
        "en": "Welcome — first-time setup",
    },
    "wizard_intro": {
        "de": "Ein paar Einstellungen, dann geht’s los. Alles lässt sich später ändern.",
        "en": "A few settings, then you’re ready. Everything can be changed later.",
    },
    "wizard_language": {"de": "Sprache / Language", "en": "Language / Sprache"},
    "wizard_lang_de": {"de": "Deutsch", "en": "German"},
    "wizard_lang_en": {"de": "Englisch", "en": "English"},
    "wizard_export": {"de": "Export-Verzeichnis", "en": "Export folder"},
    "wizard_export_beside": {
        "de": "Neben der Quelldatei (…/export)",
        "en": "Beside the source file (…/export)",
    },
    "wizard_export_project": {
        "de": "Projektordner ./export",
        "en": "Project folder ./export",
    },
    "wizard_export_custom": {
        "de": "Eigenen Pfad angeben",
        "en": "Enter a custom path",
    },
    "wizard_export_path": {
        "de": "Pfad zum Export-Ordner:",
        "en": "Path to the export folder:",
    },
    "wizard_work": {"de": "Index-Arbeitsordner", "en": "Index work folder"},
    "wizard_work_cache": {
        "de": "Schnell-Cache (~/.cache) — empfohlen",
        "en": "Fast cache (~/.cache) — recommended",
    },
    "wizard_work_beside": {
        "de": "Neben der Quelldatei (.step-work)",
        "en": "Beside the source file (.step-work)",
    },
    "wizard_work_custom": {
        "de": "Eigenen Pfad angeben",
        "en": "Enter a custom path",
    },
    "wizard_work_path": {
        "de": "Pfad zum Index-Ordner:",
        "en": "Path to the index folder:",
    },
    "wizard_color": {"de": "Darstellung", "en": "Appearance"},
    "wizard_color_on": {"de": "Farbe an", "en": "Color on"},
    "wizard_color_off": {"de": "Ohne Farbe", "en": "No color"},
    "wizard_done": {
        "de": "Einstellungen gespeichert. Viel Erfolg!",
        "en": "Settings saved. You’re good to go!",
    },
    "wizard_saved_to": {"de": "Gespeichert unter", "en": "Saved to"},
    "settings_title": {"de": "Einstellungen", "en": "Settings"},
    "settings_language": {"de": "Sprache ändern", "en": "Change language"},
    "settings_export": {"de": "Export-Verzeichnis", "en": "Export folder"},
    "settings_work": {"de": "Index-Arbeitsordner", "en": "Index work folder"},
    "settings_color": {"de": "Farben ein/aus", "en": "Toggle colors"},
    "settings_numbered": {
        "de": "Nummern-Präfix beim Export",
        "en": "Number prefix on export",
    },
    "settings_numbered_on": {
        "de": "an (1_ 2_ 3_ …)",
        "en": "on (1_ 2_ 3_ …)",
    },
    "settings_numbered_off": {"de": "aus", "en": "off"},
    "settings_rerun": {
        "de": "Ersteinrichtung erneut",
        "en": "Run setup wizard again",
    },
    "settings_show": {"de": "Aktuelle Werte anzeigen", "en": "Show current values"},
    "settings_back": {"de": "Zurück", "en": "Back"},
    "color_on": {"de": "Farbe: an", "en": "Color: on"},
    "color_off": {"de": "Farbe: aus", "en": "Color: off"},
    "source_title": {"de": "Quelldatei wählen", "en": "Choose source file"},
    "source_prompt": {"de": "Pfad zur STEP-Datei:", "en": "Path to the STEP file:"},
    "source_missing": {"de": "Datei nicht gefunden", "en": "File not found"},
    "source_not_step": {
        "de": "Keine STEP-Datei (erwartet .stp / .step): {name}",
        "en": "Not a STEP file (expected .stp / .step): {name}",
    },
    "work_prompt_title": {"de": "Index-Ordner", "en": "Index folder"},
    "work_prompt": {
        "de": "Pfad zum Arbeitsordner (leer = Einstellung nutzen):",
        "en": "Work folder path (empty = use settings):",
    },
    "cancelled": {"de": "Abgebrochen.", "en": "Cancelled."},
    "error": {"de": "Fehler", "en": "Error"},
    "need_index": {
        "de": "Bitte zuerst „Index einlesen“.",
        "en": "Please build the index first.",
    },
    "press_enter": {
        "de": "Enter = zurück zum Menü…",
        "en": "Enter = back to menu…",
    },
    "tty_required": {
        "de": "Dieses Menü braucht ein interaktives Terminal.",
        "en": "This menu needs an interactive terminal.",
    },
    "tree_header": {"de": "Strukturbaum", "en": "Structure tree"},
    "tree_footer": {
        "de": "←→ auf/zuklappen  Leertaste=markieren  i=Info  e=export  /=suchen  h=Hilfe  q=zurück",
        "en": "←→ expand/collapse  space=mark  i=info  e=export  /=search  h=help  q=back",
    },
    "tree_help_title": {"de": "Tastaturhilfe", "en": "Keyboard help"},
    "tree_body": {"de": "Körper", "en": "body"},
    "tree_cycle": {"de": "Zyklus", "en": "cycle"},
    "tree_info_title": {"de": "Knoten-Info", "en": "Node info"},
    "tree_info_file": {
        "de": "Datei / Wurzel: {name}",
        "en": "File / root: {name}",
    },
    "tree_info_roots": {
        "de": "Root-Produktdefinitionen: {n}",
        "en": "Root product definitions: {n}",
    },
    "tree_info_name": {"de": "Name: {value}", "en": "Name: {value}"},
    "tree_info_pd": {
        "de": "PRODUCT_DEFINITION: #{value}",
        "en": "PRODUCT_DEFINITION: #{value}",
    },
    "tree_info_product": {"de": "PRODUCT: #{value}", "en": "PRODUCT: #{value}"},
    "tree_info_ident": {
        "de": "Produkt-ID (ident): {value}",
        "en": "Product id (ident): {value}",
    },
    "tree_info_formation": {
        "de": "PRODUCT_DEFINITION_FORMATION: #{value}",
        "en": "PRODUCT_DEFINITION_FORMATION: #{value}",
    },
    "tree_info_children": {
        "de": "Kinder im Baum: {value}  (Baugruppen-Links: {usages})",
        "en": "Tree children: {value}  (assembly links: {usages})",
    },
    "tree_info_shape": {
        "de": "Geometrie verknüpft: {value}  (SHAPE-Links: {links})",
        "en": "Geometry linked: {value}  (SHAPE links: {links})",
    },
    "tree_info_body": {
        "de": "Anzeige-Knoten: Körper / Solid (kein eigenes PRODUCT)",
        "en": "Display node: body / solid (not a separate PRODUCT)",
    },
    "tree_info_cycle": {
        "de": "Hinweis: Zyklus in der Baugruppe",
        "en": "Note: cycle in the assembly",
    },
    "tree_info_path": {
        "de": "Pfad: {value}",
        "en": "Path: {value}",
    },
    "tree_info_usage_header": {
        "de": "Vorkommen in der Baugruppe:",
        "en": "Occurrence in the assembly:",
    },
    "tree_info_usage_id": {
        "de": "  Usage / NAUO: #{value}",
        "en": "  Usage / NAUO: #{value}",
    },
    "tree_info_usage_parent": {
        "de": "  Elternteil: {value}",
        "en": "  Parent: {value}",
    },
    "tree_info_usage_type": {
        "de": "  Typ: {value}",
        "en": "  Type: {value}",
    },
    "tree_info_designator": {
        "de": "  Bezeichnung: {value}",
        "en": "  Designator: {value}",
    },
    "tree_status_mark": {
        "de": "{n} Knoten markiert",
        "en": "{n} node(s) marked",
    },
    "tree_status_clear": {
        "de": "Auswahl gelöscht",
        "en": "selection cleared",
    },
    "tree_status_export_empty": {
        "de": "nichts markiert — zuerst Leertaste",
        "en": "nothing marked — press space first",
    },
    "tree_status_done": {"de": "Export beendet", "en": "export finished"},
    "export_progress_title": {"de": "Export", "en": "Export"},
    "export_step_prepare": {"de": "Vorbereitung", "en": "Preparing"},
    "export_step_closure": {"de": "Abhängigkeiten sammeln", "en": "Collecting dependencies"},
    "export_step_backward": {"de": "Zusatz-Entitäten", "en": "Adding references"},
    "export_backward_detail": {
        "de": "Durchlauf {pass_n}/{passes}: {checked}/{total} · +{added}",
        "en": "Pass {pass_n}/{passes}: {checked}/{total} · +{added}",
    },
    "export_closure_detail": {
        "de": "{selected} ausgewählt · {queued} in Warteschlange",
        "en": "{selected} selected · {queued} queued",
    },
    "export_step_write": {"de": "STEP schreiben", "en": "Writing STEP"},
    "export_step_done": {"de": "Fertig", "en": "Done"},
    "export_node_of": {
        "de": "Objekt {index}/{total}: {name}",
        "en": "Object {index}/{total}: {name}",
    },
    "export_done_ok": {
        "de": "Export abgeschlossen",
        "en": "Export complete",
    },
    "export_done_fail": {
        "de": "Export mit Fehlern beendet",
        "en": "Export finished with errors",
    },
    "export_done_cancel": {
        "de": "Export abgebrochen",
        "en": "Export cancelled",
    },
    "tree_help": {
        "de": (
            "Navigation      Pfeiltasten ↑↓ / j k\n"
            "                Bild↑ Bild↓, Pos1, Ende\n"
            "Aufklappen      →  oder  Enter\n"
            "Zuklappen       ←\n"
            "Unterbaum       a  (begrenzt)\n"
            "Alles zukl.     c\n"
            "Markieren       Leertaste\n"
            "Auswahl weg     x\n"
            "Knoten-Info     i\n"
            "Suchen          /   dann n = nächster Treffer\n"
            "Exportieren     e   (markierte Knoten inkl. Unterbaum)\n"
            "Hilfe           h\n"
            "Zurück          q\n"
            "\n"
            "Markierte Knoten werden jeweils als eigene STEP-Datei geschrieben."
        ),
        "en": (
            "Navigate        arrow keys ↑↓ / j k\n"
            "                PgUp PgDn, Home, End\n"
            "Expand          →  or  Enter\n"
            "Collapse        ←\n"
            "Subtree         a  (bounded)\n"
            "Collapse all    c\n"
            "Mark            space\n"
            "Clear marks     x\n"
            "Node info       i\n"
            "Search          /   then n = next hit\n"
            "Export          e   (marked nodes including subtree)\n"
            "Help            h\n"
            "Back            q\n"
            "\n"
            "Each marked node is written as its own STEP file."
        ),
    },
}


class I18n:
    def __init__(self, language: str = "de") -> None:
        self.language = language if language in {"de", "en"} else "de"

    def set_language(self, language: str) -> None:
        self.language = language if language in {"de", "en"} else "de"

    def t(self, key: str, **kwargs: Any) -> str:
        entry = STRINGS.get(key, {})
        text = entry.get(self.language) or entry.get("en") or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text


# Module-level helper used before a Session exists.
_i18n = I18n("de")


def get_i18n() -> I18n:
    return _i18n


def set_language(language: str) -> I18n:
    _i18n.set_language(language)
    return _i18n
