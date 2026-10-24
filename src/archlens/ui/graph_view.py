"""Interactive local dependency graph view."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

from archlens.core.graph import DependencyGraph
from archlens.core.models import Package


class PackageNode(QGraphicsEllipseItem):
    def __init__(self, name: str, center: QPointF, color: QColor) -> None:
        super().__init__(-90, -26, 180, 52)
        self.package_name = name
        self.setPos(center)
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#7f8caa"), 1.5))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        label = QGraphicsTextItem(name, self)
        label.setDefaultTextColor(QColor("#f2f4f8"))
        label.setFont(QFont("sans", 9))
        label.setPos(-label.boundingRect().width() / 2, -label.boundingRect().height() / 2)


class GraphView(QWidget):
    node_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setBackgroundBrush(QBrush(QColor("#171a21")))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.scene.selectionChanged.connect(self._selection_changed)

    def show_package(self, package: Package, graph: DependencyGraph) -> None:
        self.scene.clear()
        center = QPointF(0, 0)
        nodes: dict[str, PackageNode] = {
            package.name: PackageNode(package.name, center, QColor("#2f6fed"))
        }
        dependencies = sorted(graph.deps.get(package.name, ()))
        required_by = sorted(graph.rdeps.get(package.name, ()))
        for index, name in enumerate(dependencies):
            nodes[name] = PackageNode(
                name, QPointF(-280, (index - (len(dependencies) - 1) / 2) * 85), QColor("#2c8c68")
            )
        for index, name in enumerate(required_by):
            nodes[name] = PackageNode(
                name, QPointF(280, (index - (len(required_by) - 1) / 2) * 85), QColor("#8b5fbf")
            )
        for name in dependencies:
            self._line(nodes[name].pos(), center)
        for name in required_by:
            self._line(center, nodes[name].pos())
        for node in nodes.values():
            self.scene.addItem(node)
        self.scene.setSceneRect(QRectF(-480, -360, 960, 720))
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.view.scale(factor, factor)

    def _line(self, start: QPointF, end: QPointF) -> None:
        line = QGraphicsLineItem(start.x(), start.y(), end.x(), end.y())
        line.setPen(QPen(QColor("#68728a"), 1.5))
        self.scene.addItem(line)

    def _selection_changed(self) -> None:
        selected = self.scene.selectedItems()
        if selected and isinstance(selected[0], PackageNode):
            self.node_selected.emit(selected[0].package_name)
