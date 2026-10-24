# ArchLens

ArchLens is an Arch Linux package dependency analyzer. It provides a standalone
PySide6 window with package search, sorting, orphan analysis, removal estimates,
cache inspection, and package details. Core code has no Qt dependency.

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

With no arguments, the command starts the Qt application:

```sh
python -m archlens
```

The application reads the local pacman database in the background and does not
depend on caelestia-shell.

The `closure` and `freed` results are estimates. The GUI always performs a
pacman dry-run before removal and requires explicit confirmation. The app never
runs pacman as root; only the confirmed child process uses `pkexec`.

## Desktop installation

For a local editable install, the `archlens` command is created by pip:

```sh
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/archlens
```

For a local checkout, install a user-local launcher and desktop entry with one
command:

```sh
bash scripts/install_desktop.sh
```

The script creates or updates `.venv`, installs ArchLens, puts the launcher in
`~/.local/bin`, and installs an executable desktop entry and icon in
`~/.local/share`. It does not require `sudo` or modify system directories.

The desktop entry template is in `data/archlens.desktop`; package maintainers
can install it and the icon system-wide instead.

See [docs/PRD.md](docs/PRD.md), [docs/Architecture.md](docs/Architecture.md),
and [docs/pacman-verification.md](docs/pacman-verification.md) for the source
specification and verified command behavior.
