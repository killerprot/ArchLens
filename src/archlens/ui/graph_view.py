"""Interactive local dependency graph view."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

from archlens.core.graph import DependencyGraph
from archlens.core.models import Package


class PackageNode(QGraphicsObject):
    """Self-contained, clickable package node rendered directly by Qt."""

    clicked = Signal(str)

    def __init__(
        self,
        name: str,
        center: QPointF,
        color: QColor,
        selected: bool = False,
        text_color: QColor | None = None,
        accent_color: QColor | None = None,
    ) -> None:
        super().__init__()
        self.package_name = name
        self.color = color
        self._selected = selected
        self._hovered = False
        self._text_color = text_color or QColor("#f2f4f8")
        self._accent_color = accent_color or QColor("#ffffff")
        self.setPos(center)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsFocusable)

    def boundingRect(self) -> QRectF:
        return QRectF(-100, -30, 200, 60)

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self.update()

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.boundingRect().adjusted(2, 2, -2, -2)
        fill = self.color.lighter(115) if self._hovered else self.color
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(self._accent_color if self._selected else QColor("#7f8caa"), 3 if self._selected else 1.5))
        painter.drawRoundedRect(rect, 12, 12)

        font = QFont("sans", 9)
        metrics = QFontMetrics(font)
        label = metrics.elidedText(self.package_name, Qt.TextElideMode.ElideMiddle, int(rect.width() - 18))
        painter.setFont(font)
        painter.setPen(QPen(self._text_color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.package_name)
            event.accept()
            return
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)


class DependencyEdge(QGraphicsPathItem):
    """Curved directed edge with a small arrowhead."""

    def __init__(self, start: QPointF, end: QPointF) -> None:
        super().__init__()
        self.start = start
        self.end = end
        self.setZValue(-1)
        path = QPainterPath(start)
        midpoint = (start.x() + end.x()) / 2
        path.cubicTo(QPointF(midpoint, start.y()), QPointF(midpoint, end.y()), end)
        self.setPath(path)

    def paint(self, painter: QPainter, _option, _widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#68728a"), 1.5))
        painter.setBrush(QBrush(QColor("#68728a")))
        painter.drawPath(self.path())

        dx = self.end.x() - (self.end.x() + self.start.x()) / 2
        angle = math.atan2(0, dx)
        size = 8
        left = self.end - QPointF(math.cos(angle - math.pi / 6) * size, math.sin(angle - math.pi / 6) * size)
        right = self.end - QPointF(math.cos(angle + math.pi / 6) * size, math.sin(angle + math.pi / 6) * size)
        painter.drawPolygon(QPolygonF((self.end, left, right)))


class ZoomGraphicsView(QGraphicsView):
    """Graphics view with mouse-wheel zooming and an effectively unbounded canvas."""

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class GraphView(QWidget):
    node_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(QRectF(-100000, -100000, 200000, 200000))
        self._rebuilding = False
        self._nodes: dict[str, PackageNode] = {}
        self.view = ZoomGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setBackgroundBrush(self.view.palette().brush(self.view.palette().ColorRole.Base))
        self._text_color = self.view.palette().color(QPalette.ColorRole.Text)
        self._accent_color = self.view.palette().color(QPalette.ColorRole.Highlight)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def show_package(self, package: Package, graph: DependencyGraph) -> None:
        self._rebuilding = True
        self.scene.clear()
        self._nodes = {}
        center = QPointF(0, 0)
        self._add_node(package.name, center, QColor("#2f6fed"), selected=True)
        dependencies = sorted(graph.deps.get(package.name, ()))
        required_by = sorted(graph.rdeps.get(package.name, ()))
        for index, name in enumerate(dependencies):
            self._add_node(
                name,
                QPointF(-300, (index - (len(dependencies) - 1) / 2) * 90),
                QColor("#2c8c68"),
            )
        for index, name in enumerate(required_by):
            self._add_node(
                name,
                QPointF(300, (index - (len(required_by) - 1) / 2) * 90),
                QColor("#8b5fbf"),
            )
        for name in dependencies:
            self._add_edge(self._nodes[name].pos(), center)
        for name in required_by:
            self._add_edge(center, self._nodes[name].pos())
        for node in self._nodes.values():
            self.scene.addItem(node)
        content_rect = self.scene.itemsBoundingRect().adjusted(-90, -90, 90, 90)
        self.view.fitInView(content_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._rebuilding = False

    def _add_node(self, name: str, center: QPointF, color: QColor, selected: bool = False) -> None:
        node = PackageNode(
            name,
            center,
            color,
            selected=selected,
            text_color=self._text_color,
            accent_color=self._accent_color,
        )
        node.clicked.connect(self._node_clicked)
        self._nodes[name] = node

    def _add_edge(self, start: QPointF, end: QPointF) -> None:
        self.scene.addItem(DependencyEdge(start, end))

    def _node_clicked(self, package_name: str) -> None:
        if self._rebuilding or package_name not in self._nodes:
            return
        for name, node in self._nodes.items():
            node.set_selected(name == package_name)
        QTimer.singleShot(0, lambda: self.node_selected.emit(package_name))
