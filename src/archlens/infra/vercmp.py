"""Safe adapter for pacman's read-only version comparator."""

import shutil
import subprocess

from archlens.core.aur import valid_version


def vercmp_versions(left: str, right: str) -> int | None:
    if not valid_version(left) or not valid_version(right):
        return None
    binary = shutil.which("vercmp")
    if binary is None:
        return None
    try:
        result = subprocess.run([binary, left, right], capture_output=True, text=True, timeout=5, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    try:
        value = int(result.stdout.strip())
    except ValueError:
        return None
    return value if value in {-1, 0, 1} else None
