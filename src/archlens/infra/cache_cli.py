"""Safe cache cleanup through pacman-contrib's paccache."""

from __future__ import annotations

import shutil
import subprocess


class CacheCleanupError(RuntimeError):
    """Raised when cache cleanup cannot be started safely."""


def clear_old_versions(
    keep_versions: int = 2,
    *,
    confirmed: bool = False,
    pkexec: str = "pkexec",
) -> subprocess.CompletedProcess[str]:
    if keep_versions < 1:
        raise CacheCleanupError("keep_versions must be at least 1")
    if not confirmed:
        raise CacheCleanupError("explicit confirmation is required before cache cleanup")
    if shutil.which("paccache") is None:
        raise CacheCleanupError("paccache is not installed; install pacman-contrib first")
    return subprocess.run(
        [pkexec, "paccache", f"-rk{keep_versions}"],
        check=False,
        capture_output=True,
        text=True,
    )
