"""Parser for the local pacman database."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from archlens.core.models import Package, Reason
from archlens.infra.source import PackageSource


def _fields(path: Path) -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            current = None
        elif line.startswith("%") and line.endswith("%"):
            current = line
            result.setdefault(current, [])
        elif current is not None:
            result[current].append(line)
    return {key: tuple(values) for key, values in result.items()}


def _one(fields: dict[str, tuple[str, ...]], key: str, default: str = "") -> str:
    values = fields.get(key, ())
    return values[0] if values else default


class LocalPacmanSource(PackageSource):
    """Read package records from ``/var/lib/pacman/local``.

    ``foreign_file`` is useful for fixture sources. On a real system the
    foreign set comes from the read-only ``pacman -Qmq`` command.
    """

    def __init__(
        self,
        db_path: str | Path = "/var/lib/pacman/local",
        pacman: str = "pacman",
        foreign_file: str | Path | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.pacman = pacman
        self.foreign_file = Path(foreign_file) if foreign_file else None

    def _foreign_names(self) -> frozenset[str] | None:
        if self.foreign_file is not None:
            try:
                return frozenset(
                    line.strip()
                    for line in self.foreign_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            except OSError:
                return None
        try:
            completed = subprocess.run(
                [self.pacman, "-Qmq"],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return frozenset(line.strip() for line in completed.stdout.splitlines() if line.strip())

    def load(self) -> tuple[Package, ...]:
        foreign = self._foreign_names()
        packages: list[Package] = []
        for package_dir in sorted(path for path in self.db_path.iterdir() if path.is_dir()):
            desc_path = package_dir / "desc"
            depends_path = package_dir / "depends"
            if not desc_path.is_file():
                continue
            desc = _fields(desc_path)
            depends = _fields(depends_path) if depends_path.is_file() else {}
            dependency_fields = {
                key: depends.get(key, desc.get(key, ()))
                for key in ("%DEPENDS%", "%OPTDEPENDS%", "%PROVIDES%")
            }
            timestamp = int(_one(desc, "%INSTALLDATE%", "0"))
            packages.append(
                Package(
                    name=_one(desc, "%NAME%"),
                    version=_one(desc, "%VERSION%"),
                    description=_one(desc, "%DESC%"),
                    installed_size=int(_one(desc, "%SIZE%", "0")),
                    reason=Reason(int(_one(desc, "%REASON%", "0"))),
                    install_date=datetime.fromtimestamp(timestamp, tz=UTC),
                    depends=dependency_fields["%DEPENDS%"],
                    optdepends=dependency_fields["%OPTDEPENDS%"],
                    provides=dependency_fields["%PROVIDES%"],
                    is_foreign=None if foreign is None else _one(desc, "%NAME%") in foreign,
                )
            )
        return tuple(packages)
