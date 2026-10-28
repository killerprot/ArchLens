from pathlib import Path

from archlens.core.analysis import (
    blocked_by,
    explain_why,
    freed_size,
    removal_closure,
)
from archlens.core.graph import DependencyGraph
from archlens.core.usage import UsageStatus, compute_usage, optional_only, orphans, unrequired
from archlens.infra.local_db import LocalPacmanSource

FIXTURE = Path(__file__).parent / "fixtures" / "fake_pacman_db"


def graph() -> DependencyGraph:
    return DependencyGraph(LocalPacmanSource(FIXTURE, foreign_file=FIXTURE / "foreign.txt").load())


def test_strict_usage_classifies_hard_and_optional_reverse_edges() -> None:
    item = graph()
    usage = compute_usage(item)
    assert "orphan" in orphans(item)
    assert "optional-orphan" in optional_only(item)
    assert usage["optional-orphan"].status is UsageStatus.OPTIONAL_ONLY
    assert usage["cycle-a"].status is UsageStatus.REQUIRED
    assert usage["provider-a"].ambiguous is True


def test_unrequired_matches_qdt_and_qdtt_semantics() -> None:
    item = graph()
    assert "optional-orphan" not in unrequired(item, 1)
    assert "optional-orphan" in unrequired(item, 2)
    assert "orphan" in unrequired(item, 1)


def test_explain_why_returns_shortest_reverse_chain() -> None:
    assert explain_why(graph(), "leaf") == ("leaf", "low", "middle", "explicit-app")
    assert explain_why(graph(), "orphan") is None


def test_removal_closure_has_three_dependency_levels_and_no_cycle_expansion() -> None:
    item = graph()
    assert removal_closure(item, {"explicit-app"}) == frozenset(
        {"explicit-app", "middle", "low", "leaf"}
    )
    assert removal_closure(item, {"cycle-a"}) == frozenset({"cycle-a"})
    assert freed_size(item, {"explicit-app"}) == 1600


def test_blocked_uses_all_provider_breakage_semantics() -> None:
    item = graph()
    assert blocked_by(item, {"provider-a"}) == {}
    assert blocked_by(item, {"provider-a", "provider-b"}) == {
        "virtual-user": ("virtual-feature",)
    }
