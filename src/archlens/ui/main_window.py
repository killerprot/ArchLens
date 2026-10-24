"""Main ArchLens window."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from archlens.app.workers import LoadPackagesTask
from archlens.core.analysis import orphans
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.strings import (
    APP_TITLE,
    LOAD_ERROR,
    LOADING,
    ORPHANS_TOTAL,
    PACKAGES_LOADED,
    SEARCH_PLACEHOLDER,
    TAB_ORPHANS,
    TAB_PACKAGES,
)
from archlens.ui.package_detail import PackageDetail
from archlens.ui.package_table import PackageFilterModel, PackageTableModel, format_size


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 700)
        self.thread_pool = QThreadPool.globalInstance()
        self.load_task: LoadPackagesTask | None = None
        self.graph: DependencyGraph | None = None
        self.packages: tuple[Package, ...] = ()
        self.detail = PackageDetail()
        self.tabs = QTabWidget()
        self.package_model = PackageTableModel()
        self.package_proxy = PackageFilterModel()
        self.package_proxy.setSourceModel(self.package_model)
        self.package_view = self._make_table(self.package_proxy)
        self.orphan_model = PackageTableModel()
        self.orphan_proxy = PackageFilterModel()
        self.orphan_proxy.setSourceModel(self.orphan_model)
        self.orphan_view = self._make_table(self.orphan_proxy)
        self._build_ui()
        self.statusBar().showMessage(LOADING)
        self._load()

    def _make_table(self, model: PackageFilterModel) -> QTableView:
        view = QTableView()
        view.setModel(model)
        view.setSortingEnabled(True)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        view.horizontalHeader().setStretchLastSection(True)
        view.clicked.connect(self._package_selected)
        return view

    def _build_ui(self) -> None:
        packages_page = QWidget()
        packages_layout = QVBoxLayout(packages_page)
        search = QLineEdit()
        search.setPlaceholderText(SEARCH_PLACEHOLDER)
        search.textChanged.connect(self.package_proxy.setFilterFixedString)
        packages_layout.addWidget(search)
        packages_splitter = QSplitter()
        packages_splitter.addWidget(self.package_view)
        packages_splitter.addWidget(self.detail)
        packages_splitter.setStretchFactor(0, 3)
        packages_splitter.setStretchFactor(1, 2)
        packages_layout.addWidget(packages_splitter)
        self.tabs.addTab(packages_page, TAB_PACKAGES)

        orphan_page = QWidget()
        orphan_layout = QVBoxLayout(orphan_page)
        self.orphan_summary = QLabel()
        orphan_layout.addWidget(self.orphan_summary)
        orphan_layout.addWidget(self.orphan_view)
        self.tabs.addTab(orphan_page, TAB_ORPHANS)
        self.setCentralWidget(self.tabs)

    def _load(self) -> None:
        task = LoadPackagesTask()
        self.load_task = task
        task.signals.loaded.connect(self._loaded)
        task.signals.failed.connect(self._load_failed)
        self.thread_pool.start(task)

    def _loaded(self, packages: tuple[Package, ...], graph: DependencyGraph) -> None:
        self.packages = packages
        self.graph = graph
        self.package_model.set_packages(packages)
        orphan_items = orphans(graph)
        self.orphan_model.set_packages(tuple(item.package for item in orphan_items))
        total = sum(item.package.installed_size for item in orphan_items if not item.optionally_required)
        self.orphan_summary.setText(ORPHANS_TOTAL.format(count=len(orphan_items), size=format_size(total)))
        self.statusBar().showMessage(PACKAGES_LOADED.format(count=len(packages)))

    def _load_failed(self, error: str) -> None:
        self.statusBar().showMessage(LOAD_ERROR.format(error=error))

    def _package_selected(self, index) -> None:
        if self.graph is None:
            return
        source_index = self.package_proxy.mapToSource(index)
        package = self.package_model.data(source_index, Qt.UserRole)
        if isinstance(package, Package):
            self.detail.show_package(package, self.graph)
