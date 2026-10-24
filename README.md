# ArchLens

ArchLens is a read-only Arch Linux package dependency analyzer. The current
milestone contains the local pacman database parser, an in-memory dependency
graph, orphan analysis, removal estimates, and a small CLI. Core code has no
Qt dependency.

## Development

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
pytest
ruff check .
```

For Fish, either use the same explicit `.venv/bin/...` commands, or activate
the environment with `source .venv/bin/activate.fish`. Do not source the Bash
file `.venv/bin/activate` from Fish.

## CLI

All commands below only read the local pacman database:

```sh
python -m archlens orphans
python -m archlens explain package-name
python -m archlens closure package-name
python -m archlens freed package-name
python scripts/verify_closure.py
python scripts/verify_unrequired.py
```

The `closure` and `freed` results are estimates. Before any future removal
feature, pacman's dry-run result must override them and an explicit confirmation
must still be required. This milestone never runs a modifying pacman command.

See [docs/PRD.md](docs/PRD.md), [docs/Architecture.md](docs/Architecture.md),
and [docs/pacman-verification.md](docs/pacman-verification.md) for the source
specification and verified command behavior.
