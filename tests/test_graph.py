from pathlib import Path

from archlens.core.graph import DependencyGraph, dependency_name
from archlens.infra.local_db import LocalPacmanSource

FIXTURE = Path(__file__).parent / "fixtures" / "fake_pacman_db"


def graph() -> DependencyGraph:
    return DependencyGraph(LocalPacmanSource(FIXTURE, foreign_file=FIXTURE / "foreign.txt").load())


def test_dependency_name_ignores_version_constraint() -> None:
    assert dependency_name("libfoo.so=1-64") == "libfoo.so"
    assert dependency_name("glibc>=2.38") == "glibc"
    assert dependency_name("bash") == "bash"


def test_provides_and_exact_name_resolution() -> None:
    item = graph()
    assert item.resolved("virtual-user", "virtual-feature") == frozenset(
        {"provider-a", "provider-b"}
    )
    assert item.resolved("virtual-user", "shared") == frozenset({"shared"})
    assert ("virtual-user", "virtual-feature") in item.ambiguous_dependencies


def test_cycles_are_present_but_marked_for_closure_protection() -> None:
    item = graph()
    assert item.is_in_cycle("cycle-a")
    assert item.is_in_cycle("cycle-b")


def test_reverse_edges_use_needed_semantics() -> None:
    item = graph()
    assert item.rdeps["provider-a"] == frozenset({"virtual-user"})
    assert item.rdeps["provider-b"] == frozenset({"virtual-user"})


def test_core_does_not_import_qt() -> None:
    for path in Path(__file__).parents[1].joinpath("src/archlens/core").glob("*.py"):
        assert "PySide" not in path.read_text(encoding="utf-8")
