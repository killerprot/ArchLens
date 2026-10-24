"""Read-only pacman dry-run and explicitly confirmed removal."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from archlens.core.protection import protected_packages


class RemovalSafetyError(RuntimeError):
    """Raised when the removal safety protocol was not followed."""


@dataclass(frozen=True)
class DryRunResult:
    requested: tuple[str, ...]
    targets: tuple[str, ...]
    stdout: str
    stderr: str
    command: tuple[str, ...]


class PacmanCli:
    def __init__(self, pacman: str = "pacman", pkexec: str = "pkexec") -> None:
        self.pacman = pacman
        self.pkexec = pkexec

    def dry_run(self, packages: list[str] | tuple[str, ...]) -> DryRunResult:
        requested = tuple(packages)
        command = (self.pacman, "-Rs", "--print", *requested)
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        if result.returncode:
            raise RemovalSafetyError(result.stderr.strip() or "pacman dry-run failed")
        targets = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
        return DryRunResult(requested, targets, result.stdout, result.stderr, command)

    def remove(
        self,
        packages: list[str] | tuple[str, ...],
        dry_run: DryRunResult | None,
        confirmed: bool,
        protected: set[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        requested = tuple(packages)
        forbidden = sorted(set(requested) & protected_packages(protected))
        if forbidden:
            raise RemovalSafetyError(f"protected packages cannot be removed: {', '.join(forbidden)}")
        if dry_run is None or dry_run.requested != requested:
            raise RemovalSafetyError("a matching dry-run is required before removal")
        if not confirmed:
            raise RemovalSafetyError("explicit confirmation is required before removal")
        command = [self.pkexec, self.pacman, "-Rns", "--noconfirm", *requested]
        return subprocess.run(command, check=False, capture_output=True, text=True)
