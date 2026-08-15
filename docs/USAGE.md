# User guide

StepSplit lets you explore a STEP assembly and export selected parts without
loading the full geometry into a CAD viewer first.

## Typical workflow

1. Index the source STEP file once (structure and entity offsets on disk).
2. Browse the assembly tree, search for parts, check node details.
3. Mark the subtrees you need and export each as a separate `.step` file.
4. Import those smaller files into Fusion 360 or another CAD tool, one at a time.

The index lives under `~/.cache/stepsplit/`. Later runs skip a full re-index when
the same file name and size are still there.

## Interactive menu

```bash
python3 stepsplit.py
```

| Key / option | Action |
|--------------|--------|
| 1 | Choose or change STEP source file (`.stp` / `.step` only) |
| 2 | Build or resume index (Ctrl+C is safe; continues next time) |
| 3 | Open structure tree browser |
| 4 | Settings (language, export path, numbered exports, …) |
| 5 | Quit |

### First-time setup

The wizard sets UI language (English or German), export location, and index
cache location. Menu and tree strings follow that language.

## Structure tree browser

From menu option 3, or:

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
| h | Help overlay |
| q | Quit (marks stay for the session) |

During multi-object export the progress view scrolls (↑↓, PgUp/PgDn, mouse
wheel). Ctrl+C cancels the remaining exports.

## Export layout

Files are written under:

```text
{export_dir}/{source_filename}/{index_build_id}/{assembly_path}/{name}.step
```

- `index_build_id`: timestamp of the index build (e.g. `20260810-003653`)
- `assembly_path`: folders matching the tree path
- `name`: product name from the STEP file

Optional numbered exports (`1_name.step`, `2_name.step`, …) can be enabled in
settings.

## Settings file

Path: `~/.config/stepsplit/settings.json`

| Setting | Meaning |
|---------|---------|
| `language` | `en` or `de` (UI only; docs stay English) |
| `export_mode` | `beside_source`, `project_export`, or `custom` |
| `work_mode` | `cache` (default), `beside_source`, or `custom` |
| `numbered_exports` | Prefix filenames with selection order |
| `overwrite_exports` | Replace existing export files |

## Resume and progress

- Indexing: byte progress, entity count, ETA. Ctrl+C, then option 2 to continue.
- Export: per-object status; a partial batch can often be resumed.
- Cache: after a good index the full STEP structure is not re-read unless you
  force rebuild or the source size changes.

## Validation

Index integrity:

```bash
python3 stepsplit.py validate /path/file.stp
```

Exported file (dangling references):

```bash
python3 stepsplit.py check /path/export/Part.step
```

## Tips for large assemblies

- Index once, export many times from the same cache.
- Prefer exporting sub-assemblies over thousands of leaf parts when you can.
- In Fusion 360, import the exported files one by one instead of the original
  multi-GB assembly.
- Use `export --dry-run` to preview a selection before writing files.

See [CLI reference](CLI.md) for scripting.
