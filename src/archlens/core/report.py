"""Exportable package analysis reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from archlens.core.graph import DependencyGraph
from archlens.core.usage import compute_usage, optional_only, orphans


def report_data(
    graph: DependencyGraph,
    estimates: dict[str, int],
    statuses: dict[str, str],
) -> dict[str, Any]:
    usage = compute_usage(graph)
    packages = []
    for package in graph.packages:
        packages.append(
            {
                "name": package.name,
                "version": package.version,
                "description": package.description,
                "installed_size": package.installed_size,
                "reason": package.reason.name.lower(),
                "install_date": package.install_date.isoformat(),
                "depends": list(package.depends),
                "optdepends": list(package.optdepends),
                "provides": list(package.provides),
                "required_by": sorted(graph.rdeps.get(package.name, ())),
                "optional_for": list(usage[package.name].optional_for),
                "usage_status": usage[package.name].status.value,
                "ambiguous": usage[package.name].ambiguous,
                "is_foreign": package.is_foreign,
                "freed_estimate": estimates.get(package.name),
                "status": statuses.get(package.name),
            }
        )
    return {
        "application": "ArchLens",
        "packages": packages,
        "orphans": sorted(orphans(graph)),
        "optional_only": sorted(optional_only(graph)),
    }


def write_report(
    path: str | Path,
    graph: DependencyGraph,
    estimates: dict[str, int],
    statuses: dict[str, str],
) -> None:
    output = Path(path)
    data = report_data(graph, estimates, statuses)
    if output.suffix.lower() == ".md":
        output.write_text(render_markdown(data), encoding="utf-8")
    else:
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
            "# ArchLens report",
            "",
            "| Name | Version | Installed size | Reason | Freed estimate | Status |",
            "|---|---|---:|---|---:|---|",
        ]
    for package in data["packages"]:
        estimate = package["freed_estimate"]
        lines.append(
            f"| {package['name']} | {package['version']} | {package['installed_size']} | "
            f"{package['reason']} | {estimate if estimate is not None else '—'} | "
            f"{package['status'] or ''} |"
        )
    return "\n".join(lines) + "\n"
