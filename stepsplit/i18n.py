"""German / English UI strings."""

from __future__ import annotations

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    "app_title": {"de": "StepSplit", "en": "StepSplit"},
    "nav_footer": {
        "de": "↑↓ bewegen   Enter auswählen   q zurück",
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
        "de": (
            "Wähle die STEP-Datei (.stp / .step), die du aufteilen möchtest.\n"
            "Der Index-Ordner wird daraus abgeleitet und bleibt unverändert "
            "an der Quelldatei."
        ),
        "en": (
            "Pick the STEP file (.stp / .step) you want to split.\n"
            "The index folder is derived from that file. The source itself "
            "is never modified."
        ),
    },
    "menu_index": {"de": "Index erstellen", "en": "Build index"},
    "menu_index_hint": {
        "de": (
            "Liest die Baugruppen-Struktur ein und speichert Entity-Positionen "
            "im Cache.\n"
            "Kann bei großen Dateien länger dauern. Mit Ctrl+C abbrechen und "
            "später fortsetzen."
        ),
        "en": (
            "Reads the assembly structure and stores entity positions in the cache.\n"
            "Large files can take a while. Interrupt with Ctrl+C and resume later."
        ),
    },
    "menu_resume": {"de": "Index fortsetzen", "en": "Resume index"},
    "menu_resume_hint": {
        "de": (
            "Setzt einen unterbrochenen Indexaufbau an der letzten Position fort.\n"
            "Bereits gelesene Daten bleiben erhalten."
        ),
        "en": (
            "Continues an interrupted index build from the last saved position.\n"
            "Data already scanned is kept."
        ),
    },
    "menu_browse": {"de": "Strukturbaum öffnen", "en": "Open structure tree"},
    "menu_browse_hint": {
        "de": (
            "Öffnet den Strukturbaum der Baugruppe.\n"
            "Teile und Unterbaugruppen können ausgewählt und als eigene "
            "STEP-Dateien exportiert werden."
        ),
        "en": (
            "Opens the assembly structure tree.\n"
            "Parts and sub-assemblies can be selected and exported as "
            "separate STEP files."
        ),
    },
    "menu_status": {"de": "Status / Prüfung", "en": "Status / validate"},
    "menu_status_hint": {
        "de": (
            "Zeigt den Index-Status und prüft Baugruppen-Verknüpfungen.\n"
            "\n"
            "Aktuell: {state}"
        ),
        "en": (
            "Shows index status and checks assembly relationships.\n"
            "\n"
            "Current: {state}"
        ),
    },
    "menu_cache": {"de": "Cache verwalten", "en": "Manage cache"},
    "menu_cache_hint": {
        "de": (
            "Übersicht der gespeicherten Indexes mit Größe und Erstelldatum.\n"
            "Einträge einzeln oder komplett löschen.\n"
            "\n"
            "Belegt: {size}"
        ),
        "en": (
            "List cached indexes with size and creation time.\n"
            "Delete individual entries or the whole cache.\n"
            "\n"
            "Used: {size}"
        ),
    },
    "menu_settings": {"de": "Einstellungen", "en": "Settings"},
    "menu_settings_hint": {
        "de": (
            "Sprache, Export- und Index-Ordner, Farben und Nummern-Präfix ändern.\n"
            "Die Ersteinrichtung kann von hier erneut gestartet werden."
        ),
        "en": (
            "Change language, export and index folders, colors, and number prefixes.\n"
            "You can also re-run the first-time setup from here."
        ),
    },
    "menu_rebuild": {"de": "Index neu aufbauen", "en": "Rebuild index"},
    "menu_rebuild_hint": {
        "de": (
            "Löscht den bestehenden Index und liest die Datei komplett neu ein.\n"
            "Nötig, wenn sich die Quelldatei geändert hat. Je nach Größe kann "
            "das länger dauern."
        ),
        "en": (
            "Deletes the existing index and rescans the whole file.\n"
            "Needed when the source file changed. This can take a while depending "
            "on file size."
        ),
    },
    "menu_quit": {"de": "Beenden", "en": "Quit"},
    "menu_quit_hint": {
        "de": "Speichert die Einstellungen und beendet StepSplit.",
        "en": "Saves settings and exits StepSplit.",
    },
    "label_file": {"de": "Datei", "en": "File"},
    "label_size": {"de": "Größe", "en": "Size"},
    "label_index": {"de": "Index", "en": "Index"},
    "label_work": {"de": "Index-Ordner", "en": "Index folder"},
    "label_export": {"de": "Export", "en": "Export"},
    "label_cache": {"de": "Cache", "en": "Cache"},
    "label_offsets": {"de": "Direktzugriff", "en": "Random access"},
    "label_settings": {"de": "Einstellungen", "en": "Settings"},
    "value_unset": {"de": "-", "en": "-"},
    "source_none": {
        "de": "Keine Datei ausgewählt",
        "en": "No file selected",
    },
    "cache_title": {"de": "Index-Cache", "en": "Index cache"},
    "cache_root_line": {
        "de": "Ordner: {path}",
        "en": "Folder: {path}",
    },
    "cache_total_line": {
        "de": "Belegt: {size}",
        "en": "Used: {size}",
    },
    "cache_entry_hint": {
        "de": "{size}  ·  {created}",
        "en": "{size}  ·  {created}",
    },
    "cache_delete_all": {
        "de": "Gesamten Cache löschen",
        "en": "Delete entire cache",
    },
    "cache_delete_all_hint": {
        "de": "{n} Einträge löschen",
        "en": "remove {n} entries",
    },
    "cache_delete_all_hint_one": {
        "de": "1 Eintrag löschen",
        "en": "remove 1 entry",
    },
    "cache_delete_title": {"de": "Cache löschen", "en": "Delete cache"},
    "cache_confirm_delete_one": {
        "de": (
            "Diesen Cache-Eintrag wirklich löschen?\n"
            "Beim nächsten Öffnen der Baugruppe muss der Index neu erstellt werden."
        ),
        "en": (
            "Delete this cache entry?\n"
            "The assembly will need to be re-indexed the next time you open it."
        ),
    },
    "cache_confirm_delete_all": {
        "de": (
            "{n} Cache-Einträge löschen ({size})?\n"
            "Danach muss jede betroffene Baugruppe neu indexiert werden, "
            "wenn sie wieder benötigt wird."
        ),
        "en": (
            "Delete {n} cache entries ({size})?\n"
            "Each affected assembly will need to be re-indexed when you need it again."
        ),
    },
    "cache_detail_size": {"de": "Größe: {size}", "en": "Size: {size}"},
    "cache_detail_created": {
        "de": "Erstellt: {created}",
        "en": "Created: {created}",
    },
    "cache_detail_source": {
        "de": "Quelle: {path}",
        "en": "Source: {path}",
    },
    "cache_deleted_one": {
        "de": "Cache gelöscht: {name}",
        "en": "Cache deleted: {name}",
    },
    "cache_deleted_n": {
        "de": "{n} Cache-Einträge gelöscht",
        "en": "Deleted {n} cache entries",
    },
    "label_yes": {"de": "ja", "en": "yes"},
    "label_no": {"de": "nein", "en": "no"},
    "confirm_ok": {"de": "Fortfahren?", "en": "Continue?"},
    "confirm_index": {
        "de": (
            "{name}  ({size})\n\n"
            "Index jetzt erstellen?\n"
            "Je nach Dateigröße kann das länger dauern."
        ),
        "en": (
            "{name}  ({size})\n\n"
            "Build the index now?\n"
            "This can take a while depending on file size."
        ),
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
        "de": "Index erstellt",
        "en": "Index built successfully",
    },
    "index_done_fail": {"de": "fehlgeschlagen / unterbrochen", "en": "failed / interrupted"},
    "press_key": {
        "de": "Taste drücken → zurück zum Hauptmenü",
        "en": "Press a key → back to main menu",
    },
    "progress_footer": {
        "de": "↑↓ / Mausrad scrollen   Ctrl+C abbrechen",
        "en": "↑↓ / mouse wheel scroll   Ctrl+C interrupts",
    },
    "progress_done_footer": {
        "de": "↑↓ scrollen   Enter → zurück",
        "en": "↑↓ scroll   Enter → back",
    },
    "scan_progress_label": {
        "de": "Index wird erstellt",
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
        "de": "{count} Einträge · {scanned} Datensätze",
        "en": "{count} entries · {scanned} records",
    },
    "scan_enrich_finish": {
        "de": "{count} Einträge",
        "en": "{count} entries",
    },
    "index_missing": {
        "de": "Noch kein Index. Zuerst „Index erstellen“ wählen.",
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
        "de": "Der Index gehört zu einer anderen Datei. Bitte neu erstellen.",
        "en": "Index belongs to a different source file: rebuild it.",
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
        "de": " (kein Direktzugriff-Index)",
        "en": " (no random-access index)",
    },
    "index_detail_no_candidates": {
        "de": " (Zusatzliste für Export fehlt)",
        "en": " (export helper list missing)",
    },
    "index_detail_progress": {
        "de": "{percent:.1f}% ({bytes})",
        "en": "{percent:.1f}% ({bytes})",
    },
    "index_candidates_hint": {
        "de": "Export-Hilfsliste fehlt. Ein weiterer Durchlauf kann sie erzeugen.",
        "en": "Export helper list missing: one extra pass can build it.",
    },
    "index_readonly_hint": {
        "de": "Die Quelldatei bleibt unverändert. Fortschritt wird angezeigt. Mit Ctrl+C abbrechen, später fortsetzen.",
        "en": "Read-only source. Progress follows. Ctrl+C resumes later.",
    },
    "status_section_check": {"de": "Prüfung", "en": "Checks"},
    "status_no_check": {
        "de": "Keine Prüfung möglich: Index fehlt oder ist unvollständig.",
        "en": "No check possible: index missing or incomplete.",
    },
    "sev_ok": {"de": "OK", "en": "OK"},
    "sev_warn": {"de": "WARN", "en": "WARN"},
    "sev_fail": {"de": "FEHLER", "en": "FAIL"},
    "val_result_ok": {
        "de": "Ergebnis: für den Export geeignet",
        "en": "Result: usable for export",
    },
    "val_result_bad": {
        "de": "Ergebnis: NICHT für den Export geeignet",
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
        "de": "Keine Baugruppen-Verknüpfungen — die Datei enthält keine Unterbaugruppen (einzelnes Teil oder flache Struktur).",
        "en": "No assembly links — the file has no subassemblies (single part or flat structure).",
    },
    "val_no_usages_multi": {
        "de": "Keine Baugruppen-Verknüpfungen trotz mehrerer Bauteile. Oft eine flache Datei ohne Hierarchie; falls Unterbaugruppen erwartet werden, ggf. Usage-Typ prüfen.",
        "en": "No assembly links despite multiple parts. Often a flat file without hierarchy; if subassemblies were expected, check the usage entity type.",
    },
    "val_n_usages": {
        "de": "{n} Baugruppen-Verknüpfungen indexiert.",
        "en": "{n} assembly usages indexed.",
    },
    "val_fallback_usages": {
        "de": "{n} Verknüpfungen wurden aus nachgestellten Referenzen gelesen (nicht aus Positionsargumenten). Bitte Stichprobe prüfen.",
        "en": "{n} usages parsed from trailing references instead of positional args: verify a sample.",
    },
    "val_dangling_usages": {
        "de": "{parents} Verknüpfungen zeigen auf ein unbekanntes Elternteil, {children} auf ein unbekanntes Kind.",
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
        "de": "{n} Produktdefinitionen ohne PRODUCT_DEFINITION_SHAPE. Struktur ohne Geometrie.",
        "en": "{n} product definitions have no PRODUCT_DEFINITION_SHAPE: structure without geometry.",
    },
    "val_shapes_ok": {
        "de": "Jede Produktdefinition hat verknüpfte Geometrie.",
        "en": "Every product definition has a shape.",
    },
    "val_no_roots": {
        "de": "Keine Wurzel-Produktdefinition gefunden. Der Baugruppen-Graph ist vermutlich zyklisch.",
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
        "de": "Zyklus gefunden: {n} Produktdefinition(en) betroffen ({preview})",
        "en": "{n} product definition(s) sit on a cycle: {preview}",
    },
    "val_acyclic": {
        "de": "Der Baugruppen-Graph ist azyklisch.",
        "en": "The assembly graph is acyclic.",
    },
    "val_ambiguous_names": {
        "de": "{n} Produktnamen gehören zu mehr als einer Definition. Bitte mit „#id“ auswählen.",
        "en": "{n} product names map to more than one product definition; select by '#id'.",
    },
    "err_no_usages_export": {
        "de": "Keine Baugruppen-Verknüpfungen gefunden. Export ist nicht möglich.",
        "en": "No assembly usages: export unsafe.",
    },
    "err_no_roots": {
        "de": "Keine Wurzelknoten.",
        "en": "No root nodes.",
    },
    "aborted": {"de": "Abgebrochen.", "en": "Aborted."},
    "ok_short": {"de": "OK", "en": "OK"},
    "wizard_welcome": {
        "de": "Willkommen zur Ersteinrichtung",
        "en": "Welcome to first-time setup",
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
        "de": "Cache unter ~/.cache (empfohlen)",
        "en": "Fast cache (~/.cache), recommended",
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
        "de": "Einstellungen gespeichert.",
        "en": "Settings saved.",
    },
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
        "de": "Ersteinrichtung erneut starten",
        "en": "Run setup wizard again",
    },
    "settings_back": {"de": "Zurück", "en": "Back"},
    "color_on": {"de": "an", "en": "on"},
    "color_off": {"de": "aus", "en": "off"},
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
        "de": "Bitte zuerst „Index erstellen“.",
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
        "de": "←→ auf-/zuklappen  Leertaste=markieren  i=Info  e=exportieren  /=suchen  h=Hilfe  q=zurück",
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
        "de": "Wurzel-Produktdefinitionen: {n}",
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
        "de": "Anzeige-Knoten: Körper/Solid (kein eigenes PRODUCT)",
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
        "de": "Nichts markiert. Zuerst mit Leertaste auswählen.",
        "en": "nothing marked (press space first)",
    },
    "tree_status_done": {"de": "Export beendet", "en": "export finished"},
    "export_progress_title": {"de": "Export", "en": "Export"},
    "export_step_prepare": {"de": "Vorbereitung", "en": "Preparing"},
    "export_step_closure": {"de": "Abhängigkeiten sammeln", "en": "Collecting dependencies"},
    "export_step_backward": {"de": "Zusatzreferenzen", "en": "Adding references"},
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
            "Alles zuklappen c\n"
            "Markieren       Leertaste\n"
            "Markierung weg  x\n"
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
