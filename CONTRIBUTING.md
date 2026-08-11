# Contributing

Thank you for improving StepSplit.

## Development setup

```bash
git clone https://github.com/Myjestic/stepsplit.git
cd stepsplit
python3 -m unittest discover -s tests -t .
```

No pip dependencies. Python 3.10+ required.

## Before you commit

**Do not commit STEP files.** The repo gitignores `*.stp` and `*.step` except synthetic fixtures under `tests/`. Always check:

```bash
git status
git ls-files | grep -iE '\.(stp|step)$'
```

If any real assembly file appears, unstage it before committing.

## Running tests

```bash
python3 -m unittest discover -s tests -t . -v
```

TUI tests require a PTY and are skipped automatically in environments without one (e.g. some CI sandboxes). GitHub Actions Ubuntu runners run them successfully.

## Code style

- Match existing module layout under `stepsplit/`
- Keep changes focused; avoid unrelated refactors
- UI strings go through `stepsplit/i18n.py` (English and German)
- Docs in English under `docs/`

## Pull requests

1. Describe the problem and solution
2. Note how you tested (command + sample file type/size if relevant — do not attach customer STEP files)
3. Ensure tests pass

## Reporting issues

Use GitHub issues. For security concerns, see [SECURITY.md](../SECURITY.md).
