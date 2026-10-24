from unittest.mock import patch

import pytest

from archlens.infra.pacman_cli import DryRunResult, PacmanCli, RemovalSafetyError


def dry_run() -> DryRunResult:
    return DryRunResult(("demo",), ("demo-1.0-1",), "demo-1.0-1\n", "", ("pacman",))


def test_dry_run_uses_argument_list_and_returns_targets() -> None:
    completed = type("Completed", (), {"returncode": 0, "stdout": "demo-1.0-1\n", "stderr": ""})()
    with patch("archlens.infra.pacman_cli.subprocess.run", return_value=completed) as run:
        result = PacmanCli().dry_run(["demo"])
    run.assert_called_once_with(("pacman", "-Rs", "--print", "demo"), check=False, capture_output=True, text=True)
    assert result.targets == ("demo-1.0-1",)


def test_removal_requires_matching_dry_run_and_confirmation() -> None:
    cli = PacmanCli()
    with pytest.raises(RemovalSafetyError):
        cli.remove(["demo"], None, confirmed=True)
    with pytest.raises(RemovalSafetyError):
        cli.remove(["demo"], dry_run(), confirmed=False)
    with pytest.raises(RemovalSafetyError):
        cli.remove(["glibc"], dry_run(), confirmed=True)


def test_removal_uses_pkexec_only_after_confirmation() -> None:
    completed = type("Completed", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    with patch("archlens.infra.pacman_cli.subprocess.run", return_value=completed) as run:
        PacmanCli().remove(["demo"], dry_run(), confirmed=True)
    run.assert_called_once_with(
        ["pkexec", "pacman", "-Rns", "--noconfirm", "demo"],
        check=False,
        capture_output=True,
        text=True,
    )
