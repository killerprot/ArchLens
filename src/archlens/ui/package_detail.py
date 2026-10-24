"""Package detail widget."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from archlens.core.analysis import explain_why
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.strings import text


class PackageDetail(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.language = "en"
        self.package: Package | None = None
        self.graph: DependencyGraph | None = None
        self.layout = QVBoxLayout(self)
        self.labels = [QLabel(text("no_selection")) for _ in range(5)]
        for label in self.labels:
            label.setWordWrap(True)
            self.layout.addWidget(label)
        self.layout.addStretch()

    def show_package(self, package: Package, graph: DependencyGraph) -> None:
        self.package = package
        self.graph = graph
        self._render()

    def set_language(self, language: str) -> None:
        self.language = language
        if self.package is None or self.graph is None:
            for label in self.labels:
                label.setText(text("no_selection", language))
            return
        self._render()

    def _render(self) -> None:
        assert self.package is not None and self.graph is not None
        package = self.package
        graph = self.graph
        why = explain_why(graph, package.name)
        dependencies = ", ".join(package.depends) or text("none", self.language)
        required_by = ", ".join(sorted(graph.rdeps.get(package.name, ()))) or text("none", self.language)
        why_text = " → ".join(why) if why else "—"
        values = (
            f"<b>{package.name} {package.version}</b>",
            f"{text('description', self.language)}: {package.description}",
            f"{text('direct_dependencies', self.language)}: {dependencies}",
            f"{text('required_by', self.language)}: {required_by}",
            f"{text('why_installed', self.language)}: {why_text}",
        )
        for label, value in zip(self.labels, values):
            label.setText(value)
