"""Background removal dry-run task."""

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from archlens.infra.pacman_cli import DryRunResult, PacmanCli


class DryRunSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class DryRunTask(QRunnable):
    def __init__(self, packages: tuple[str, ...]) -> None:
        super().__init__()
        self.packages = packages
        self.signals = DryRunSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.completed.emit(PacmanCli().dry_run(self.packages))
        except Exception as error:  # noqa: BLE001 - report failure to the GUI
            self.signals.failed.emit(str(error))


class RemovalTask(QRunnable):
    def __init__(self, packages: tuple[str, ...], dry_run: DryRunResult) -> None:
        super().__init__()
        self.packages = packages
        self.dry_run = dry_run
        self.signals = DryRunSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = PacmanCli().remove(self.packages, self.dry_run, confirmed=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "removal failed")
            self.signals.completed.emit(result)
        except Exception as error:  # noqa: BLE001 - report failure to the GUI
            self.signals.failed.emit(str(error))
