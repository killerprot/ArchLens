"""Queries over the package dependency graph."""

from __future__ import annotations

from collections import deque

from archlens.core.graph import DependencyGraph
from archlens.core.models import Orphan, Reason


def orphans(graph: DependencyGraph) -> tuple[Orphan, ...]:
    reachable = graph.reachable_from_explicit()
    optional = graph.optionally_reachable()
    return tuple(
        Orphan(package, package.name in optional)
        for package in graph.packages
        if package.reason is Reason.DEPENDENCY and package.name not in reachable
    )


def unrequired(graph: DependencyGraph, *, ignore_optional: bool = False) -> frozenset[str]:
    """Mimic ``pacman -Qdt``; set ``ignore_optional`` for ``-Qdtt``."""
    hard_required = {name for name, reverse in graph.rdeps.items() if reverse}
    if ignore_optional:
        required = hard_required
    else:
        required = hard_required | set(graph.optionally_reachable())
    return frozenset(
        package.name
        for package in graph.packages
        if package.reason is Reason.DEPENDENCY and package.name not in required
    )


def explain_why(graph: DependencyGraph, package: str) -> tuple[str, ...] | None:
    """Return the shortest reverse-dependency chain to an explicit package."""
    if package not in graph.by_name:
        raise KeyError(package)
    queue: deque[tuple[str, tuple[str, ...]]] = deque([(package, (package,))])
    visited = {package}
    while queue:
        current, path = queue.popleft()
        if graph.by_name[current].reason is Reason.EXPLICIT:
            return path
        for parent in sorted(graph.rdeps.get(current, ())):
            if parent not in visited:
                visited.add(parent)
                queue.append((parent, path + (parent,)))
    return None


def removal_closure(graph: DependencyGraph, packages: set[str] | list[str]) -> frozenset[str]:
    """Estimate the ``-Rns`` closure without adding explicit packages.

    Multiple providers are handled conservatively through needed semantics:
    all provider reverse edges must be inside the current removal set. A
    separate breakage check is available as ``blocked_by``.
    """
    removal = set(packages)
    unknown = removal - graph.by_name.keys()
    if unknown:
        raise KeyError(next(iter(unknown)))
    changed = True
    while changed:
        changed = False
        for name in tuple(removal):
            for dependency in graph.deps.get(name, ()):
                if dependency in removal:
                    continue
                if graph.by_name[dependency].reason is Reason.EXPLICIT:
                    continue
                if graph.is_in_cycle(dependency):
                    continue
                if graph.rdeps.get(dependency, frozenset()) <= removal:
                    removal.add(dependency)
                    changed = True
    return frozenset(removal)


def blocked_by(graph: DependencyGraph, packages: set[str] | list[str]) -> dict[str, tuple[str, ...]]:
    """Return outside packages whose hard dependencies break under removal."""
    removal = set(packages)
    blocked: dict[str, tuple[str, ...]] = {}
    for package in graph.by_name:
        if package in removal:
            continue
        broken = tuple(
            raw
            for raw in graph.by_name[package].depends
            if graph.resolved(package, raw) and graph.resolved(package, raw) <= removal
        )
        if broken:
            blocked[package] = broken
    return blocked


def freed_size(graph: DependencyGraph, packages: set[str] | list[str]) -> int:
    return sum(graph.by_name[name].installed_size for name in removal_closure(graph, packages))
