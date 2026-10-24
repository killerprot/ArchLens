# ArchLens

ArchLens is an Arch Linux package dependency analyzer. It provides a standalone
PySide6 window with package search, sorting, orphan analysis, removal estimates,
cache inspection, and package details. Core code has no Qt dependency.

## Development

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/ruff check .
```

For Fish, either use the same explicit `.venv/bin/...` commands, or activate
the environment with `source .venv/bin/activate.fish`. Do not source the Bash
file `.venv/bin/activate` from Fish. Using the explicit paths also avoids
Arch's externally-managed system Python environment (PEP 668).

## CLI

All commands below only read the local pacman database:

```sh
.venv/bin/python -m archlens orphans
.venv/bin/python -m archlens explain package-name
.venv/bin/python -m archlens closure package-name
.venv/bin/python -m archlens freed package-name
.venv/bin/python scripts/verify_closure.py
.venv/bin/python scripts/verify_unrequired.py
```

With no arguments, the command starts the Qt application:

```sh
.venv/bin/python -m archlens
```

The application reads the local pacman database in the background and does not
depend on caelestia-shell.

The `closure` and `freed` results are estimates. The GUI always performs a
pacman dry-run before removal and requires explicit confirmation. The app never
runs pacman as root; only the confirmed child process uses `pkexec`.

Known MVP limitations: dependency version constraints are parsed but ignored,
and virtual dependencies with multiple installed providers are deliberately
over-approximated by the estimate. The pacman dry-run is authoritative before
any removal.

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

## Build from GitHub

On Arch Linux, the AUR-style package can be built directly from the repository:

```sh
git clone https://github.com/killerprot/ArchLens.git
cd ArchLens
makepkg -si
```

This uses `PKGBUILD`, installs runtime dependencies through pacman, and places
the application and desktop files system-wide. The package build needs
`git`, `python-build`, and `python-installer` as make dependencies.

See [docs/PRD.md](docs/PRD.md), [docs/Architecture.md](docs/Architecture.md),
and [docs/pacman-verification.md](docs/pacman-verification.md) for the source
specification and verified command behavior.
