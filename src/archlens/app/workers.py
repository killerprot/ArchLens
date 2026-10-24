"""Background Qt tasks."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from archlens.core.graph import DependencyGraph
from archlens.infra.local_db import LocalPacmanSource


class LoadSignals(QObject):
    loaded = Signal(object, object)
    failed = Signal(str)


class LoadPackagesTask(QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = LoadSignals()

    @Slot()
    def run(self) -> None:
        try:
            graph = DependencyGraph(LocalPacmanSource().load())
            self.signals.loaded.emit(graph.packages, graph)
        except Exception as error:  # noqa: BLE001 - send failure to the GUI
            self.signals.failed.emit(str(error))
