"""Background cache scan task."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from archlens.core.cache_analysis import scan_cache


class CacheSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class CacheTask(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = CacheSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.completed.emit(scan_cache())
        except Exception as error:  # noqa: BLE001 - report failure to the GUI
            self.signals.failed.emit(str(error))
