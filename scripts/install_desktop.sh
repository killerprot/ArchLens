#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="$PROJECT_DIR/.venv"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
APPLICATIONS_DIR="$DATA_DIR/applications"
ICON_DIR="$DATA_DIR/icons/hicolor/scalable/apps"
DESKTOP_FILE="$APPLICATIONS_DIR/archlens.desktop"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python executable not found: $PYTHON_BIN" >&2
    exit 1
fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "Installing ArchLens into the virtual environment"
"$VENV_DIR/bin/python" -m pip install -e "$PROJECT_DIR"

mkdir -p "$BIN_DIR" "$APPLICATIONS_DIR" "$ICON_DIR"
ln -sfn "$VENV_DIR/bin/archlens" "$BIN_DIR/archlens"
cp "$PROJECT_DIR/data/archlens.svg" "$ICON_DIR/archlens.svg"

sed "s|^Exec=.*|Exec=$BIN_DIR/archlens|" \
    "$PROJECT_DIR/data/archlens.desktop" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

echo "Installed: $DESKTOP_FILE"
echo "If the launcher is not visible immediately, log out and back in or restart the file manager."
