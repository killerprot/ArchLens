from unittest.mock import patch

import pytest

from archlens.infra.cache_cli import CacheCleanupError, clear_old_versions


def test_cache_cleanup_requires_confirmation() -> None:
    with pytest.raises(CacheCleanupError):
        clear_old_versions(confirmed=False)


def test_cache_cleanup_uses_pkexec_and_paccache() -> None:
    completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    with (
        patch("archlens.infra.cache_cli.shutil.which", return_value="/usr/bin/paccache"),
        patch("archlens.infra.cache_cli.subprocess.run", return_value=completed) as run,
    ):
        clear_old_versions(keep_versions=3, confirmed=True)
    run.assert_called_once_with(
        ["pkexec", "paccache", "-rk3"],
        check=False,
        capture_output=True,
        text=True,
    )
