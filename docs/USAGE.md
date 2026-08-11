# User guide

StepSplit helps you **explore** and **export parts of a STEP assembly** without importing the full geometry into a CAD viewer first.

## Typical workflow

1. **Index** the source STEP file once (structure + entity offsets on disk).
2. **Browse** the assembly tree, search for parts, inspect node metadata.
3. **Mark** the subtrees you need and **export** each as a separate `.step` file.
4. **Import** those smaller files into Fusion 360 or another CAD tool one at a time.

Because the index is stored in SQLite under `~/.cache/stepsplit/`, step 1 is skipped on later runs for the same file (same name and size).

## Interactive menu

```bash
python3 stepsplit.py
```

| Key / option | Action |
|--------------|--------|
| 1 | Choose or change STEP source file (`.stp` / `.step` only) |
| 2 | Build or resume index (Ctrl+C safe; continues next time) |
| 3 | Open structure tree browser |
| 4 | Settings (language, export path, numbered exports, …) |
| 5 | Quit |

### First-time setup

The wizard sets UI language (**English** or **German**), export location, and index cache location. All strings in the menu and tree follow the selected language.

## Structure tree browser

Open from menu option **3** or:

```bash
python3 stepsplit.py browse /path/to/assembly.stp
```

| Key | Action |
|-----|--------|
| ↑ / ↓ or j / k | Move selection |
| ← / → or h / l | Collapse / expand node |
| Space | Mark / unmark node for export |
| e | Export marked nodes |
| / | Search by name |
| i | Show node info (PD id, child count, …) |
| a | Expand all |
| z | Collapse all |
| h | Full help overlay |
| q | Quit (marks preserved in session) |

During **multi-object export**, the progress view scrolls (↑↓, PgUp/PgDn, mouse wheel). **Ctrl+C** cancels the remaining exports.

## Export layout

Exported files are written under:

```text
{export_dir}/{source_filename}/{index_build_id}/{assembly_path}/{name}.step
```

- `index_build_id` — timestamp of the index build (e.g. `20260810-003653`)
- `assembly_path` — folder chain reflecting the tree path
- `name` — product name from the STEP file

Optional **numbered exports** (`1_name.step`, `2_name.step`, …) can be enabled in settings.

## Settings file

Config path: `~/.config/stepsplit/settings.json`

| Setting | Meaning |
|---------|---------|
| `language` | `en` or `de` (UI strings only; docs are English) |
| `export_mode` | `beside_source`, `project_export`, or `custom` |
| `work_mode` | `cache` (default), `beside_source`, or `custom` |
| `numbered_exports` | Prefix filenames with selection order |
| `overwrite_exports` | Replace existing export files |

## Resume and progress

- **Indexing**: byte-level progress, entity count, ETA. Interrupt with Ctrl+C; rerun option 2 to continue.
- **Export**: per-object status line; partial batch can be resumed depending on export state.
- **Cache**: no re-read of the full STEP structure after a successful index unless you force rebuild or the source file changes size.

## Validation

Check index integrity:

```bash
python3 stepsplit.py validate /path/file.stp
```

Check an exported file for dangling references:

```bash
python3 stepsplit.py check /path/export/Part.step
```

## Tips for large assemblies

- Index once, export many times from the same cache.
- Prefer exporting **sub-assemblies** over thousands of leaf parts when possible.
- For Fusion 360, import exported files **sequentially** rather than the original multi-GB assembly.
- Use CLI `export --dry-run` to preview selection before writing files.

See [CLI reference](CLI.md) for scripting and automation.
