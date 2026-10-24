"""Background Qt tasks."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from archlens.core.analysis import freed_size
from archlens.core.graph import DependencyGraph
from archlens.core.protection import protected_packages
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


class EstimateSignals(QObject):
    completed = Signal(object, object)
    failed = Signal(str)


class RemovalEstimateTask(QRunnable):
    def __init__(self, graph: DependencyGraph) -> None:
        super().__init__()
        self.graph = graph
        self.signals = EstimateSignals()

    @Slot()
    def run(self) -> None:
        try:
            estimates: dict[str, int] = {}
            statuses: dict[str, str] = {}
            protected = protected_packages()
            blocked = {
                next(iter(providers))
                for (consumer, _raw), providers in self.graph.requirements.items()
                if len(providers) == 1 and next(iter(providers)) != consumer
            }
            for package in self.graph.packages:
                if package.name in protected:
                    statuses[package.name] = "protected_status"
                elif package.name in blocked:
                    statuses[package.name] = "blocked_status"
                else:
                    estimates[package.name] = freed_size(self.graph, {package.name})
            self.signals.completed.emit(estimates, statuses)
        except Exception as error:  # noqa: BLE001 - report failure to the GUI
            self.signals.failed.emit(str(error))
