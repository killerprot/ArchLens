"""Compare our removal estimate with pacman's read-only print operation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archlens.core.analysis import blocked_by, removal_closure
from archlens.core.graph import DependencyGraph
from archlens.infra.local_db import LocalPacmanSource


def pacman_print(package: str) -> tuple[set[str], str | None]:
    # -Rns --print is rejected by the pacman version on this machine because
    # --nosave and --print are mutually exclusive. -Rs --print is the verified
    # read-only equivalent for dependency closure and is reported as such.
    result = subprocess.run(
        ["pacman", "-Rs", "--print", package],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        return set(), result.stderr.strip() or "command failed"
    return {line.strip().rsplit("-", 2)[0] for line in result.stdout.splitlines() if line.strip()}, None


def main() -> int:
    graph = DependencyGraph(LocalPacmanSource().load())
    packages = [package.name for package in graph.packages[:20]]
    report: list[str] = [
        "ArchLens closure verification",
        "pacman command: pacman -Rs --print (exact -Rns --print is unavailable; see docs/pacman-verification.md)",
        "",
    ]
    mismatches = 0
    for package in packages:
        ours = set(removal_closure(graph, {package}))
        theirs, error = pacman_print(package)
        blocked = blocked_by(graph, {package})
        report.append(f"[{package}]")
        if error:
            if blocked:
                report.append(
                    "  blocked-vs-not: match (pacman rejected target and our hard-dependency "
                    f"check found {sorted(blocked)})"
                )
            else:
                report.append(f"  blocked-vs-not: mismatch; pacman rejected target: {error}")
                mismatches += 1
            continue
        extra = sorted(ours - theirs)
        missing = sorted(theirs - ours)
        if extra or missing or blocked:
            mismatches += 1
        report.append(f"  ours: {sorted(ours)}")
        report.append(f"  pacman: {sorted(theirs)}")
        report.append(f"  extra packages in ours: {extra}")
        report.append(f"  missing in ours: {missing}")
        report.append(f"  blocked-vs-not: {sorted(blocked)}")
        report.append(
            "  likely cause: virtual-provider ambiguity, ignored version constraints, "
            "or pacman's transaction/provider selection"
        )
    report.append(f"\nMismatching package cases: {mismatches}/{len(packages)}")
    output = "\n".join(report) + "\n"
    print(output)
    (ROOT / "verification-report.txt").write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
