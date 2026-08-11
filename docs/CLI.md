# CLI reference

```bash
python3 stepsplit.py <command> [options] [source.stp]
```

If `source` is omitted, the default path from `stepsplit.py` is used (when that file exists on your machine).

## Global concepts

| Term | Meaning |
|------|---------|
| `source` | Input STEP assembly (`.stp` / `.step`) |
| `--work-dir PATH` | Index folder (default: `~/.cache/stepsplit/<name>-<size>/`) |
| `--output-dir PATH` | Export root (default: `./export` or settings) |

## Commands

### `index` — build the disk-backed index

```bash
python3 stepsplit.py index assembly.stp
python3 stepsplit.py index assembly.stp --force
python3 stepsplit.py index assembly.stp --structure-only
```

| Flag | Description |
|------|-------------|
| `--force` | Rebuild from scratch |
| `--no-resume` | Do not continue a partial index |
| `--structure-only` | Skip byte-offset index (smaller; export needs extra passes) |

Progress is printed to stderr. Safe to interrupt with Ctrl+C.

### `enrich` — build backward-candidate lists

```bash
python3 stepsplit.py enrich assembly.stp
python3 stepsplit.py enrich assembly.stp --force
```

Speeds up export for assemblies where geometry is linked via backward references. Run once per index if export warns about missing enrichment.

### `inspect` — index statistics (JSON)

```bash
python3 stepsplit.py inspect assembly.stp
```

### `validate` — check indexed relationships

```bash
python3 stepsplit.py validate assembly.stp
python3 stepsplit.py validate assembly.stp --samples 3
```

### `tree` — print assembly tree

```bash
python3 stepsplit.py tree assembly.stp
python3 stepsplit.py tree assembly.stp --max-depth 3
python3 stepsplit.py tree assembly.stp --json --output tree.json
python3 stepsplit.py tree assembly.stp --select 'PartName' --select '#12345'
```

Selection accepts product name, `#entity_id`, or `pd:product_definition_id`.

### `browse` — interactive curses tree

```bash
python3 stepsplit.py browse assembly.stp --output-dir ./export
```

Builds index automatically if missing (`--no-auto-index` to disable).

### `export` — batch export subtrees

```bash
python3 stepsplit.py export assembly.stp \
  --select 'FRAME_REAR' \
  --select '#164675648' \
  --output-dir ./export
```

Common export flags:

| Flag | Description |
|------|-------------|
| `--select` | Repeat for each subtree (name, `#id`, or `pd:id`) |
| `--dry-run` | List targets without writing files |
| `--parallel` | Parallel export workers (default: sequential) |
| `--backward` | Backward reference groups (`none`, `all`, or comma list) |
| `--backward-iterations N` | Depth of backward geometry pass (default: 3) |
| `--skip-check` | Skip post-export STEP validation |

### `check` — verify exported STEP references

```bash
python3 stepsplit.py check ./export/Part.step
```

### `menu` — interactive menu

```bash
python3 stepsplit.py menu
```

Same as running `python3 stepsplit.py` with no arguments.

## Examples

```bash
# Full pipeline
python3 stepsplit.py index /data/truck.stp --work-dir ~/index/truck
python3 stepsplit.py validate /data/truck.stp --work-dir ~/index/truck
python3 stepsplit.py export /data/truck.stp --work-dir ~/index/truck \
  --select 'FRAME_REAR' --output-dir ~/export/truck
python3 stepsplit.py check ~/export/truck/FRAME_REAR.step

# Preview export targets
python3 stepsplit.py export assembly.stp --select 'Part_A' --dry-run
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing file, invalid args, …) |
| 130 | Interrupted (Ctrl+C) |
