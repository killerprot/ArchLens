"""Compare unrequired package queries with pacman -Qdt and -Qdtt."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archlens.core.analysis import unrequired
from archlens.core.graph import DependencyGraph
from archlens.infra.local_db import LocalPacmanSource


def pacman_query(double_t: bool) -> set[str]:
    args = ["pacman", "-Qdttq" if double_t else "-Qdtq"]
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "pacman query failed")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def main() -> int:
    graph = DependencyGraph(LocalPacmanSource().load())
    lines = ["ArchLens unrequired verification", ""]
    for double_t in (False, True):
        ours = set(unrequired(graph, ignore_optional=double_t))
        pacman = pacman_query(double_t)
        lines.extend(
            [
                "-Qdtt" if double_t else "-Qdt",
                f"  ours only: {sorted(ours - pacman)}",
                f"  pacman only: {sorted(pacman - ours)}",
                f"  equal: {ours == pacman}",
                "",
            ]
        )
    report = "\n".join(lines)
    print(report)
    (ROOT / "unrequired-report.txt").write_text(report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
