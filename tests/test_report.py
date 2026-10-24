import json
from datetime import UTC, datetime
from pathlib import Path

from archlens.core.graph import DependencyGraph
from archlens.core.models import Package, Reason
from archlens.core.report import report_data, write_report


def graph() -> DependencyGraph:
    package = Package("demo", "1.0", "Demo", 10, Reason.EXPLICIT, datetime.now(UTC))
    return DependencyGraph((package,))


def test_report_contains_analysis_fields(tmp_path: Path) -> None:
    item = report_data(graph(), {"demo": 10}, {})["packages"][0]
    assert item["name"] == "demo"
    assert item["freed_estimate"] == 10
    output = tmp_path / "report.json"
    write_report(output, graph(), {"demo": 10}, {})
    assert json.loads(output.read_text(encoding="utf-8"))["packages"][0]["name"] == "demo"
