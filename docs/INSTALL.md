# Installation

StepSplit needs **Python 3.10+**. Indexing and export use only the standard
library. The interactive menu and structure tree need **curses** (built in on
Linux, macOS, and WSL). On Windows install `windows-curses`; StepSplit can
prompt for that on first run.

## Requirements

- Python 3.10, 3.11, or 3.12 (3.13/3.14 usually work; if `windows-curses` has
  no wheel for your build, use 3.10-3.12)
- A UTF-8 capable terminal (Windows Terminal, WSL, Linux, macOS)
- Disk space for the index cache (often a fraction of the source STEP size)
- For the UI: curses (`windows-curses` on Windows)

## Get the code

```bash
git clone https://github.com/Myjestic/stepsplit.git
cd stepsplit
```

The repo does not include STEP files. Point StepSplit at your own `.stp` /
`.step` assemblies.

## First run

```bash
python3 stepsplit.py
```

On Windows, if curses is missing you will see something like:

```text
StepSplit needs a terminal UI library that Python does not ship on Windows.
Missing module: _curses  →  install 'windows-curses'
Install 'windows-curses' now with pip? [Y/n]
```

Confirm with `Y`, or install manually:

```bat
python -m pip install windows-curses
```

On first launch a short setup asks for:

- UI language (English or German)
- Export folder (beside the source, project `export/`, or a custom path)
- Index work folder (`~/.cache/stepsplit/`, beside the source, or custom)

Settings land in:

```text
~/.config/stepsplit/settings.json
```

On Windows that is `%USERPROFILE%\.config\stepsplit\settings.json`.

## Index cache

After a successful index, reopening the same file is fast. Matching is by
**filename and size**. The SQLite index lives under:

```text
~/.cache/stepsplit/<filename>-<size>/
```

Delete that folder to force a full re-index, or use force rebuild in the menu.

## Windows notes

- Prefer Windows Terminal or a normal PowerShell/cmd window, not a tiny IDE panel.
- Run from a real folder on disk when you can. Paths like
  `\\wsl.localhost\...` can be awkward for interactive terminals.
- Use `python stepsplit.py` or `py -3 stepsplit.py`.
- Check pip with `python -m pip --version`.
- CLI without UI:

  ```bat
  python stepsplit.py index D:\path\to\assembly.stp
  python stepsplit.py tree D:\path\to\assembly.stp
  python stepsplit.py export D:\path\to\assembly.stp --select PART_NAME
  ```

## WSL / Linux notes

- Use a normal terminal for the tree browser.
- For 10+ GB files, leave enough free space on the cache partition.
- Ctrl+C stops indexing or export; the next run can resume.

## Quick checks

```bash
python3 stepsplit.py --help
python3 stepsplit.py index /path/to/assembly.stp
python3 stepsplit.py browse /path/to/assembly.stp
```

## Troubleshooting

| Issue | Hint |
|-------|------|
| `No module named '_curses'` | Windows: `python -m pip install windows-curses` (or accept the first-run prompt) |
| `windows-curses` install fails | Try Python 3.10-3.12, then pip again |
| Tree UI looks broken | Full terminal; try `TERM=xterm-256color` |
| Source STEP file not found | Pass the full path to your local `.stp` file |
| Slow first index | Expected for multi-GB files; watch the ETA |
| Old index after a file change | Size changed creates a new cache folder, or force rebuild |

See [User guide](USAGE.md) and [CLI reference](CLI.md).
