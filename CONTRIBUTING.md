# Contributing

Thanks for helping with StepSplit.

## Development setup

```bash
git clone https://github.com/Myjestic/stepsplit.git
cd stepsplit
python3 -m unittest discover -s tests -t .
```

On Linux, macOS, and WSL there are no pip dependencies. On Windows the
interactive UI needs `windows-curses` (optional; first run can install it).
Python 3.10+ is required.

## Before you commit

Do not commit STEP files. The repo ignores `*.stp` and `*.step` except synthetic
fixtures under `tests/`. Check before committing:

```bash
git status
git ls-files | grep -iE '\.(stp|step)$'
```

If a real assembly shows up, unstage it.

## Running tests

```bash
python3 -m unittest discover -s tests -t . -v
```

TUI tests need a PTY and skip automatically when none is available. GitHub
Actions Ubuntu runners usually have one.

## Code style

- Follow the layout under `stepsplit/`
- Keep changes focused
- UI strings go through `stepsplit/i18n.py` (English and German)
- Docs in English under `docs/`

## Pull requests

1. Describe the problem and the fix
2. Note how you tested (command and sample file type/size if useful; do not
   attach customer STEP files)
3. Make sure tests pass

## Reporting issues

Use GitHub issues. For security reports see [SECURITY.md](SECURITY.md).
