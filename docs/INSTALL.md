# Installation

StepSplit runs on **Python 3.10+** with the standard library only — no `pip install` required.

## Requirements

- Python 3.10, 3.11, or 3.12
- Terminal with UTF-8 support (WSL, Linux, macOS; Windows Terminal recommended)
- Enough disk space for the index cache (typically a fraction of the source STEP size)
- A curses-capable terminal for the structure tree (`browse` / menu option 3)

## Get the code

```bash
git clone git@github.com:YOUR_USER/stepsplit.git
cd stepsplit
```

The repository does **not** ship STEP files. Use your own `.stp` / `.step` assembly locally.

## First run

```bash
python3 stepsplit.py
```

On first launch, a short setup wizard asks for:

- UI language (**English** or **German**)
- Export folder (beside source, project `export/`, or custom path)
- Index work folder (cache under `~/.cache/stepsplit/`, beside source, or custom)

Settings are saved to:

```text
~/.config/stepsplit/settings.json
```

## Index cache

After the first successful index build, reopening the same file is fast — the tool matches by **filename and file size** and reuses the SQLite index under:

```text
~/.cache/stepsplit/<filename>-<size>/
```

You can delete this folder to force a full re-index, or use **Build index → force rebuild** in the menu.

## WSL / Linux notes

- Run from a normal terminal (not inside an IDE output panel) for the curses tree browser.
- For very large files (10+ GB), ensure enough free disk space on the partition holding the cache.
- Indexing and export can be interrupted with **Ctrl+C** and resumed on the next run.

## CLI smoke test

```bash
python3 stepsplit.py --help
python3 stepsplit.py index /path/to/assembly.stp
python3 stepsplit.py browse /path/to/assembly.stp
```

## Troubleshooting

| Issue | Hint |
|-------|------|
| Tree UI garbled | Set `TERM=xterm-256color`, use a full terminal |
| “Source STEP file not found” | Pass the full path to your local `.stp` file |
| Slow first index | Normal for multi-GB files; progress shows ETA |
| Old index after file change | File size changed → new cache folder; or force rebuild |

See also [User guide](USAGE.md) and [CLI reference](CLI.md).
