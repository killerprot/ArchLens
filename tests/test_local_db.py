from datetime import UTC, datetime
from pathlib import Path

from archlens.core.models import Reason
from archlens.infra.local_db import LocalPacmanSource

FIXTURE = Path(__file__).parent / "fixtures" / "fake_pacman_db"


def test_local_database_parser_reads_desc_and_depends() -> None:
    packages = LocalPacmanSource(FIXTURE, foreign_file=FIXTURE / "foreign.txt").load()
    by_name = {package.name: package for package in packages}

    assert len(packages) == 13
    assert by_name["explicit-app"].reason is Reason.EXPLICIT
    assert by_name["explicit-app"].installed_size == 1000
    assert by_name["explicit-app"].install_date == datetime.fromtimestamp(
        1700000000, tz=UTC
    )
    assert by_name["explicit-app"].depends == ("middle",)
    assert by_name["explicit-app"].optdepends == ("optional-orphan: extra feature",)
    assert by_name["provider-a"].provides == ("virtual-feature",)
    assert by_name["provider-a"].is_foreign is True
    assert by_name["middle"].is_foreign is False


def test_foreign_is_unknown_when_pacman_fails() -> None:
    packages = LocalPacmanSource(FIXTURE, pacman="does-not-exist").load()
    assert all(package.is_foreign is None for package in packages)
