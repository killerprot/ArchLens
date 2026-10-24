"""Package detail widget."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from archlens.core.analysis import explain_why
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.strings import (
    DESCRIPTION,
    DIRECT_DEPENDENCIES,
    NO_DEPENDENCIES,
    NO_SELECTION,
    REQUIRED_BY,
    WHY_INSTALLED,
)


class PackageDetail(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.labels = [QLabel(NO_SELECTION) for _ in range(5)]
        for label in self.labels:
            label.setWordWrap(True)
            self.layout.addWidget(label)
        self.layout.addStretch()

    def show_package(self, package: Package, graph: DependencyGraph) -> None:
        why = explain_why(graph, package.name)
        dependencies = ", ".join(package.depends) or NO_DEPENDENCIES
        required_by = ", ".join(sorted(graph.rdeps.get(package.name, ()))) or NO_DEPENDENCIES
        why_text = " → ".join(why) if why else "—"
        values = (
            f"<b>{package.name} {package.version}</b>",
            f"{DESCRIPTION}: {package.description}",
            f"{DIRECT_DEPENDENCIES}: {dependencies}",
            f"{REQUIRED_BY}: {required_by}",
            f"{WHY_INSTALLED}: {why_text}",
        )
        for label, value in zip(self.labels, values):
            label.setText(value)
