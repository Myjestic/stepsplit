# StepSplit

**Split multi-gigabyte STEP assemblies into smaller files — without opening them in CAD first.**

Very large STEP files (for example 13 GB with thousands of parts) overwhelm many workstations and lightweight CAD tools such as Autodesk Fusion 360. Importing the whole model loads geometry into RAM and triggers rendering — the process often fails or becomes unusably slow.

The usual workaround is to open the assembly in a full CAD system and export parts one by one. That repeats the same memory and rendering problem for every export.

**StepSplit** takes a different approach: it scans the clear-text STEP file sequentially, stores entity locations on disk, and keeps the assembly structure in a compact SQLite database. You browse the tree, pick the objects you need, and export each one as its own STEP file — with B-Rep geometry intact, but without ever loading the full model into memory or rendering it.

Inspired by a **structure-first workflow** like Kisters 3DViewStation: understand the hierarchy first, then export only what you need.

| | |
|---|---|
| **Runtime** | Python 3.10+ (stdlib only — no pip install) |
| **UI** | Terminal menu + curses tree browser (**English / German**) |
| **Formats** | STEP AP214 / AP242 (`.stp`, `.step`) |
| **Typical use** | Automotive assemblies, Creo / Solid Edge exports, Fusion 360 prep |

## The problem StepSplit solves

| Typical CAD workflow | With StepSplit |
|---------------------|----------------|
| Open entire 13 GB file in CAD | Stream-read structure only; geometry stays on disk |
| High RAM use + GPU rendering | No rendering, bounded memory |
| Export one part at a time inside CAD | Mark many nodes, batch-export from the tree |
| Restart from scratch after a crash | Index and export **resume** where you stopped |
| Re-index after every restart | Indexed files stay in **SQLite cache** |

Import the exported smaller STEP files into Fusion 360 or other tools **one at a time** — much more reliable than importing the full assembly.

## Features

- **Structure-first indexing** — read the full assembly hierarchy without loading all geometry into RAM
- **Persistent SQLite cache** — once indexed, reopen the same file instantly on the next run (matched by filename and size)
- **Interrupt and resume** — stop indexing or export with Ctrl+C and continue later
- **Live progress** — byte progress, entity counts, and ETA while indexing; per-object status while exporting
- **Bilingual UI** — menu and tree browser in **English and German** (switch in settings)
- **Collapsible structure tree** — search, fold/unfold, node info (`i`), multi-select with Space
- **Batch export** — scrollable progress view during multi-object export
- **Hierarchical export paths** — `{export}/{source}/{index-build}/{assembly path}/{name}.step`
- **Backward geometry pass** — includes solids linked only via `SHAPE_REPRESENTATION_RELATIONSHIP`
- **CLI** — index, validate, tree dump, batch export, and scripting

## Quick start

```bash
git clone https://github.com/Myjestic/stepsplit.git
cd stepsplit
python3 stepsplit.py
```

1. Choose your **STEP source file** (`.stp` / `.step`) — not included in the repo
2. **Build index** (progress bar; safe to interrupt and resume)
3. Open **structure tree**, mark nodes with **Space**, export with **e**

Settings: `~/.config/stepsplit/settings.json`  
Index cache: `~/.cache/stepsplit/<filename>-<size>/`

## Documentation

| Document | Description |
|----------|-------------|
| [Install](docs/INSTALL.md) | Requirements, WSL/Linux, first run |
| [User guide](docs/USAGE.md) | Menu, tree browser, export behaviour |
| [CLI reference](docs/CLI.md) | All commands and flags |

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
- No modification of the source STEP file (read-only)
- **No STEP files in the repository** — large assemblies, exports, and index caches are gitignored; add your own files locally

## License

[MIT](LICENSE) — you may use, copy, modify, merge, publish, distribute, sublicense, and sell copies of this software. Include the copyright notice in copies. The software is provided **as is**, without warranty.
