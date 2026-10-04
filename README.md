# StepSplit

**Open-source Python tool to split large STEP/STP assemblies (AP214 / AP242)
into smaller files without loading them into CAD or RAM.**

Trying to open a multi-gigabyte STEP file (10 GB+) and Fusion 360, FreeCAD, or
another viewer freezes or runs out of memory? Exporting part by part from a
full CAD system often hits the same wall.

StepSplit reads the STEP text sequentially, indexes the assembly structure in
SQLite, and leaves heavy B-Rep geometry on disk. Browse the tree in the
terminal, select sub-assemblies or parts, and batch-export standalone `.step`
files—without loading the whole model into memory.

| | |
|---|---|
| **Runtime** | Python 3.10+ (standard library). On Windows the menu needs `windows-curses` (first run can install it) |
| **UI** | Terminal menu and structure tree (English / German) |
| **Formats** | STEP AP214 / AP242 (`.stp`, `.step`) |
| **Typical use** | Large assemblies from Creo, Solid Edge, and similar; prep for Fusion 360 |

## Why it helps

| Usual CAD approach | With StepSplit |
|--------------------|----------------|
| Open the entire file in CAD | Read structure only; geometry stays on disk |
| High RAM and GPU load | No rendering |
| Export one part at a time inside CAD | Mark several nodes and batch-export |
| Crash means start over | Index and export can resume |
| Re-index every session | Cache is reused when name and size match |

Import the smaller exported files into Fusion 360 (or another tool) one at a
time. That is usually more reliable than importing the original assembly.

## Features

- Index the assembly structure without loading all geometry into RAM
- Keep a SQLite cache keyed by filename and size
- Interrupt indexing or export with Ctrl+C and continue later
- Progress while indexing (bytes, entity count, ETA) and while exporting
- Menu and tree in English or German
- Collapsible tree with search, node info (`i`), and multi-select (Space)
- Batch export with a scrollable progress view
- Export paths: `{export}/{source}/{index-build}/{assembly path}/{name}.step`
- Backward geometry pass for solids linked only via `SHAPE_REPRESENTATION_RELATIONSHIP`
- CLI for indexing, validation, tree dump, and scripted export

## Quick start

```bash
git clone https://github.com/Myjestic/stepsplit.git
cd stepsplit
python3 stepsplit.py
```

Or install and run the `stepsplit` command:

```bash
python3 -m pip install "git+https://github.com/Myjestic/stepsplit.git"
stepsplit
```

On Windows, the first menu start may ask to install `windows-curses`. Answer `Y`,
or install with UI support:

```bat
python -m pip install "git+https://github.com/Myjestic/stepsplit.git[windows]"
```

CLI-only commands (`index`, `tree`, `export`, `check`) work without that package.

1. Choose your STEP source file (`.stp` / `.step`). None are shipped in the repo.
2. Build the index (progress bar; safe to interrupt and resume).
3. Open the structure tree, mark nodes with Space, export with `e`.

Settings: `~/.config/stepsplit/settings.json`  
Index cache: `~/.cache/stepsplit/<filename>-<size>/`

## Documentation

| Document | Description |
|----------|-------------|
| [Install](docs/INSTALL.md) | Requirements, Windows, WSL/Linux |
| [User guide](docs/USAGE.md) | Menu, tree browser, export layout |
| [CLI reference](docs/CLI.md) | Commands and flags |

## Tests

```bash
python3 -m unittest discover -s tests -t .
```

CI runs the same suite on Ubuntu with Python 3.10 and 3.12.

## Project layout

```text
stepsplit.py          Entry point (menu + CLI)
stepsplit/            Library (scan, export, UI, …)
tests/                Unit and pipeline tests (synthetic fixtures only)
docs/                 Install, usage, CLI
```

## What is not included

- No tessellation, meshing, or CAD kernel
- The source STEP file is read-only
- No real STEP files in the repository (assemblies, exports, and caches are gitignored)

## License

[MIT](LICENSE). Use, copy, modify, and distribute freely; keep the copyright
notice. The software is provided as is, without warranty.
