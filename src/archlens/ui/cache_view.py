"""Qt model for the pacman cache."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from archlens.core.cache_analysis import CachedPackage
from archlens.strings import text
from archlens.ui.package_table import format_size


class CacheTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.entries: tuple[CachedPackage, ...] = ()
        self.language = "en"

    def set_language(self, language: str) -> None:
        self.language = language
        self.headerDataChanged.emit(Qt.Horizontal, 0, 2)

    def set_entries(self, entries: tuple[CachedPackage, ...]) -> None:
        self.beginResetModel()
        self.entries = entries
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else len(self.entries)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return 0 if parent is not None and parent.isValid() else 3

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return (text("name", self.language), text("version", self.language), text("size", self.language))[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        entry = self.entries[index.row()]
        return (entry.name, entry.version, format_size(entry.size))[index.column()]
