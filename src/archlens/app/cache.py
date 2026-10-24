"""Background cache scan task."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from archlens.core.cache_analysis import scan_cache
from archlens.infra.cache_cli import clear_old_versions


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


class CacheCleanupTask(QRunnable):
    def __init__(self, keep_versions: int = 2) -> None:
        super().__init__()
        self.keep_versions = keep_versions
        self.signals = CacheSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = clear_old_versions(self.keep_versions, confirmed=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "cache cleanup failed")
            self.signals.completed.emit(result)
        except Exception as error:  # noqa: BLE001 - report failure to the GUI
            self.signals.failed.emit(str(error))
