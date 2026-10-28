"""Package usage classification for strict orphan analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Literal

from archlens.core.graph import DependencyGraph
from archlens.core.models import Reason


class UsageStatus(Enum):
    EXPLICIT = "explicit"
    REQUIRED = "required"
    OPTIONAL_ONLY = "optional_only"
    ORPHAN = "orphan"


@dataclass(frozen=True)
class Usage:
    status: UsageStatus
    required_by: tuple[str, ...]
    optional_for: tuple[str, ...]
    ambiguous: bool = False


def compute_usage(graph: DependencyGraph) -> Mapping[str, Usage]:
    """Classify installed packages using hard and optional reverse edges.

    Hard virtual dependencies intentionally point to every provider. This is an
    over-approximation for suggestions; pacman's dry-run remains authoritative.
    """
    hard: dict[str, set[str]] = {name: set() for name in graph.by_name}
    optional: dict[str, set[str]] = {name: set() for name in graph.by_name}
    ambiguous: set[str] = set()
    for package in graph.packages:
        for raw in package.depends:
            providers = graph.resolved(package.name, raw)
            if len(providers) > 1:
                ambiguous.update(providers)
            for provider in providers:
                if provider != package.name:
                    hard[provider].add(package.name)
        for raw, providers in zip(package.optdepends, graph.optional_resolved(package.name)):
            del raw
            for provider in providers:
                if provider != package.name:
                    optional[provider].add(package.name)

    result: dict[str, Usage] = {}
    for package in graph.packages:
        required_by = tuple(sorted(hard[package.name]))
        optional_for = tuple(sorted(optional[package.name]))
        if package.reason is Reason.EXPLICIT:
            status = UsageStatus.EXPLICIT
        elif required_by:
            status = UsageStatus.REQUIRED
        elif optional_for:
            status = UsageStatus.OPTIONAL_ONLY
        else:
            status = UsageStatus.ORPHAN
        result[package.name] = Usage(status, required_by, optional_for, package.name in ambiguous)
    return MappingProxyType(result)


def orphans(graph: DependencyGraph) -> list[str]:
    usage = compute_usage(graph)
    return sorted(name for name, item in usage.items() if item.status is UsageStatus.ORPHAN)


def optional_only(graph: DependencyGraph) -> list[str]:
    usage = compute_usage(graph)
    return sorted(name for name, item in usage.items() if item.status is UsageStatus.OPTIONAL_ONLY)


def unrequired(graph: DependencyGraph, level: Literal[1, 2]) -> frozenset[str]:
    """Return the package names corresponding to ``pacman -Qdt``/``-Qdtt``."""
    if level not in (1, 2):
        raise ValueError("level must be 1 or 2")
    statuses = {UsageStatus.ORPHAN}
    if level == 2:
        statuses.add(UsageStatus.OPTIONAL_ONLY)
    usage = compute_usage(graph)
    return frozenset(name for name, item in usage.items() if item.status in statuses)
