"""Compare strict orphan estimates with pacman's read-only -Qdt queries."""

from __future__ import annotations

import subprocess

from archlens.core.graph import DependencyGraph
from archlens.core.usage import unrequired
from archlens.infra.local_db import LocalPacmanSource


def pacman_query(double_t: bool) -> set[str]:
    args = ["pacman", "-Qdttq" if double_t else "-Qdtq"]
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def compare(ours: set[str], theirs: set[str]) -> None:
    extra = sorted(ours - theirs)
    missing = sorted(theirs - ours)
    print(f"ours={len(ours)} pacman={len(theirs)}")
    print(f"extra packages in ours ({len(extra)}): {', '.join(extra) or 'none'}")
    print(f"missing packages in ours ({len(missing)}): {', '.join(missing) or 'none'}")
    if extra or missing:
        print("likely cause: local database semantics/provider resolution differ from libalpm")
    else:
        print("no mismatch")


def main() -> int:
    graph = DependencyGraph(LocalPacmanSource().load())
    for level in (1, 2):
        print(f"Qd{'t' if level == 1 else 'tt'} comparison")
        compare(set(unrequired(graph, level)), pacman_query(level == 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
