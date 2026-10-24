"""Qt models for package lists."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt

from archlens.core.models import Package, Reason
from archlens.strings import text


def format_size(size: int) -> str:
    value = float(size)
    for suffix in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or suffix == "GiB":
            return f"{value:.1f} {suffix}"
        value /= 1024
    return f"{size} B"


class PackageTableModel(QAbstractTableModel):
    def __init__(self, packages: tuple[Package, ...] = ()) -> None:
        super().__init__()
        self.packages = list(packages)
        self.freed: dict[str, int] = {}
        self.language = "en"

    def set_language(self, language: str) -> None:
        self.language = language
        self.headerDataChanged.emit(Qt.Horizontal, 0, 5)
        if self.packages:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.packages) - 1, 5))

    def _headers(self) -> tuple[str, ...]:
        return tuple(
            text(key, self.language)
            for key in ("name", "version", "size", "freed", "reason", "date")
        )

    def set_packages(self, packages: tuple[Package, ...]) -> None:
        self.beginResetModel()
        self.packages = list(packages)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        parent = parent or QModelIndex()
        return 0 if parent.isValid() else len(self.packages)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        parent = parent or QModelIndex()
        return 0 if parent.isValid() else 6

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers()[section]
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
                text("explicit", self.language)
                if package.reason is Reason.EXPLICIT
                else text("dependency", self.language),
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
