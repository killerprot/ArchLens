"""Qt models for package lists."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from archlens.core.models import Package, Reason
from archlens.strings import (
    COL_DATE,
    COL_FREED,
    COL_NAME,
    COL_REASON,
    COL_SIZE,
    COL_VERSION,
    DEPENDENCY,
    EXPLICIT,
)


def format_size(size: int) -> str:
    value = float(size)
    for suffix in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or suffix == "GiB":
            return f"{value:.1f} {suffix}"
        value /= 1024
    return f"{size} B"


class PackageTableModel(QAbstractTableModel):
    HEADERS = (COL_NAME, COL_VERSION, COL_SIZE, COL_FREED, COL_REASON, COL_DATE)

    def __init__(self, packages: tuple[Package, ...] = ()) -> None:
        super().__init__()
        self.packages = list(packages)
        self.freed: dict[str, int] = {}

    def set_packages(self, packages: tuple[Package, ...]) -> None:
        self.beginResetModel()
        self.packages = list(packages)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        parent = parent or QModelIndex()
        return 0 if parent.isValid() else len(self.packages)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        parent = parent or QModelIndex()
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        package = self.packages[index.row()]
        if role == Qt.UserRole:
            return package
        if role == Qt.DisplayRole:
            values = (
                package.name,
                package.version,
                format_size(package.installed_size),
                format_size(self.freed.get(package.name, 0)) if package.name in self.freed else "—",
                EXPLICIT if package.reason is Reason.EXPLICIT else DEPENDENCY,
                package.install_date.astimezone().strftime("%Y-%m-%d"),
            )
            return values[index.column()]
        if role == Qt.UserRole + 1:
            values = (
                package.name,
                package.version,
                package.installed_size,
                self.freed.get(package.name, 0),
                package.reason.value,
                package.install_date,
            )
            return values[index.column()]
        return None


class PackageFilterModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(0)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_value = left.data(Qt.UserRole + 1)
        right_value = right.data(Qt.UserRole + 1)
        if isinstance(left_value, datetime) and isinstance(right_value, datetime):
            return left_value < right_value
        return left_value < right_value
