"""Dependency graph with explicit needed and breakage semantics."""

from __future__ import annotations

import re
from collections import defaultdict, deque

from archlens.core.models import Package

_OPERATOR = re.compile(r"(>=|<=|=|>|<)")


def dependency_name(raw: str) -> str:
    """Return the name part; version constraints are intentionally ignored in MVP."""
    return _OPERATOR.split(raw, maxsplit=1)[0]


class DependencyGraph:
    """In-memory graph of installed packages.

    ``deps`` uses needed semantics: a virtual dependency points to every
    installed provider. This over-approximates need and therefore avoids
    suggesting removal too aggressively. Removal blocking uses the separate
    ``requirements`` mapping and only blocks when all providers are removed.
    """

    def __init__(self, packages: tuple[Package, ...] | list[Package]) -> None:
        self.packages = tuple(packages)
        self.by_name = {package.name: package for package in self.packages}
        self.providers: dict[str, frozenset[str]] = {}
        provider_sets: defaultdict[str, set[str]] = defaultdict(set)
        for package in self.packages:
            for provided in package.provides:
                provider_sets[dependency_name(provided)].add(package.name)
        self.providers = {name: frozenset(names) for name, names in provider_sets.items()}

        self.requirements: dict[tuple[str, str], frozenset[str]] = {}
        deps: defaultdict[str, set[str]] = defaultdict(set)
        rdeps: defaultdict[str, set[str]] = defaultdict(set)
        ambiguous: set[tuple[str, str]] = set()
        for package in self.packages:
            for raw in package.depends:
                names = self._resolve(raw)
                self.requirements[(package.name, raw)] = names
                if len(names) > 1:
                    ambiguous.add((package.name, raw))
                deps[package.name].update(names)
                for name in names:
                    rdeps[name].add(package.name)
        self.deps = {name: frozenset(deps[name]) for name in self.by_name}
        self.rdeps = {name: frozenset(rdeps[name]) for name in self.by_name}
        self.ambiguous_dependencies = frozenset(ambiguous)

    def _resolve(self, raw: str) -> frozenset[str]:
        name = dependency_name(raw)
        if name in self.by_name:
            return frozenset((name,))
        return self.providers.get(name, frozenset()) & self.by_name.keys()

    def resolved(self, package: str, raw: str) -> frozenset[str]:
        return self.requirements.get((package, raw), self._resolve(raw))

    def optional_resolved(self, package: str) -> tuple[frozenset[str], ...]:
        item = self.by_name[package]
        return tuple(self._resolve(raw.split(":", maxsplit=1)[0].strip()) for raw in item.optdepends)

    def breaks_dependency(self, package: str, removal: set[str]) -> bool:
        """Whether an installed package would lose one hard dependency."""
        return any(
            providers and providers <= removal
            for raw in self.by_name[package].depends
            for providers in (self.resolved(package, raw),)
        )

    def is_in_cycle(self, package: str) -> bool:
        """Return whether hard dependency edges can reach the package again."""
        todo = list(self.deps.get(package, ()))
        visited: set[str] = set()
        while todo:
            current = todo.pop()
            if current == package:
                return True
            if current not in visited:
                visited.add(current)
                todo.extend(self.deps.get(current, ()))
        return False

    def reachable_from_explicit(self) -> frozenset[str]:
        reachable: set[str] = set()
        todo = deque(package.name for package in self.packages if package.reason.value == 0)
        while todo:
            name = todo.popleft()
            if name in reachable:
                continue
            reachable.add(name)
            todo.extend(self.deps.get(name, ()))
        return frozenset(reachable)

    def optionally_reachable(self) -> frozenset[str]:
        """Packages reachable after crossing at least one optdepend edge."""
        marked: set[str] = set()
        todo: deque[str] = deque()
        for package in self.packages:
            for providers in self.optional_resolved(package.name):
                todo.extend(providers)
        while todo:
            name = todo.popleft()
            if name in marked:
                continue
            marked.add(name)
            todo.extend(self.deps.get(name, ()))
            for providers in self.optional_resolved(name):
                todo.extend(providers)
        return frozenset(marked)
