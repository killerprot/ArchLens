"""Main ArchLens window."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from archlens.app.cache import CacheTask
from archlens.app.removal import DryRunTask, RemovalTask
from archlens.app.workers import LoadPackagesTask
from archlens.core.analysis import orphans
from archlens.core.cache_analysis import CachedPackage, cache_total
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.core.protection import protected_packages
from archlens.infra.pacman_cli import DryRunResult
from archlens.strings import LANGUAGES, text
from archlens.ui.cache_view import CacheTableModel
from archlens.ui.package_detail import PackageDetail
from archlens.ui.package_table import PackageFilterModel, PackageTableModel, format_size


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "en"
        self.setWindowTitle(text("app_title"))
        self.resize(1100, 700)
        self.setStyleSheet(
            """
            QMainWindow { background: palette(window); }
            QLineEdit, QComboBox { padding: 6px; border-radius: 5px; }
            QTableView { alternate-background-color: palette(alternate-base); }
            QHeaderView::section { padding: 6px; font-weight: 600; }
            QTabBar::tab { padding: 8px 16px; }
            QLabel#detailPanel { padding: 12px; }
            """
        )
        self.thread_pool = QThreadPool.globalInstance()
        self.load_task: LoadPackagesTask | None = None
        self.graph: DependencyGraph | None = None
        self.packages: tuple[Package, ...] = ()
        self.selected_package: Package | None = None
        self.dry_run_task: DryRunTask | None = None
        self.removal_task: RemovalTask | None = None
        self.cache_task: CacheTask | None = None
        self.detail = PackageDetail()
        self.detail.setObjectName("detailPanel")
        self.tabs = QTabWidget()
        self.language_combo = QComboBox()
        for code, label in LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.currentIndexChanged.connect(self._language_changed)
        self.package_model = PackageTableModel()
        self.package_proxy = PackageFilterModel()
        self.package_proxy.setSourceModel(self.package_model)
        self.package_view = self._make_table(self.package_proxy)
        self.orphan_model = PackageTableModel()
        self.orphan_proxy = PackageFilterModel()
        self.orphan_proxy.setSourceModel(self.orphan_model)
        self.orphan_view = self._make_table(self.orphan_proxy)
        self.cache_model = CacheTableModel()
        self._build_ui()
        self.statusBar().showMessage(text("loading", self.language))
        self._load()
        self._scan_cache()

    def _make_table(self, model: PackageFilterModel) -> QTableView:
        view = QTableView()
        view.setModel(model)
        view.setSortingEnabled(True)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        view.horizontalHeader().setStretchLastSection(True)
        view.clicked.connect(lambda index, proxy=model: self._package_selected(index, proxy))
        return view

    def _build_ui(self) -> None:
        packages_page = QWidget()
        packages_layout = QVBoxLayout(packages_page)
        self.search = QLineEdit()
        self.search.textChanged.connect(self.package_proxy.setFilterFixedString)
        packages_layout.addWidget(self.search)
        self.remove_button = QPushButton()
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self._request_removal)
        packages_layout.addWidget(self.remove_button)
        packages_splitter = QSplitter()
        packages_splitter.addWidget(self.package_view)
        packages_splitter.addWidget(self.detail)
        packages_splitter.setStretchFactor(0, 3)
        packages_splitter.setStretchFactor(1, 2)
        packages_layout.addWidget(packages_splitter)
        self.tabs.addTab(packages_page, "")

        orphan_page = QWidget()
        orphan_layout = QVBoxLayout(orphan_page)
        self.orphan_summary = QLabel()
        orphan_layout.addWidget(self.orphan_summary)
        orphan_layout.addWidget(self.orphan_view)
        self.tabs.addTab(orphan_page, "")

        cache_page = QWidget()
        cache_layout = QVBoxLayout(cache_page)
        self.cache_summary = QLabel()
        self.cache_view = QTableView()
        self.cache_view.setModel(self.cache_model)
        self.cache_view.horizontalHeader().setStretchLastSection(True)
        cache_layout.addWidget(self.cache_summary)
        cache_layout.addWidget(self.cache_view)
        self.tabs.addTab(cache_page, "")

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.language_combo)
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(toolbar)
        root_layout.addWidget(self.tabs)
        self.setCentralWidget(root)
        self._retranslate()

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
        self.package_view.resizeColumnsToContents()
        self.orphan_view.resizeColumnsToContents()
        self._update_orphan_summary(orphan_items)
        self.statusBar().showMessage(text("packages_loaded", self.language, count=len(packages)))

    def _load_failed(self, error: str) -> None:
        self.statusBar().showMessage(text("load_error", self.language, error=error))

    def _package_selected(self, index, proxy: PackageFilterModel) -> None:
        if self.graph is None:
            return
        source_index = proxy.mapToSource(index)
        model = proxy.sourceModel()
        package = model.data(source_index, Qt.UserRole)
        if isinstance(package, Package):
            self.selected_package = package
            self.remove_button.setEnabled(package.name not in protected_packages())
            self.detail.show_package(package, self.graph)

    def _language_changed(self, index: int) -> None:
        self.language = self.language_combo.itemData(index)
        self._retranslate()

    def _update_orphan_summary(self, orphan_items) -> None:
        total = sum(item.package.installed_size for item in orphan_items if not item.optionally_required)
        self.orphan_summary.setText(
            text("orphans_total", self.language, count=len(orphan_items), size=format_size(total))
        )

    def _retranslate(self) -> None:
        self.setWindowTitle(text("app_title", self.language))
        self.tabs.setTabText(0, text("tab_packages", self.language))
        self.tabs.setTabText(1, text("tab_orphans", self.language))
        self.tabs.setTabText(2, text("tab_cache", self.language))
        self.search.setPlaceholderText(text("search", self.language))
        self.remove_button.setText(text("remove_selected", self.language))
        self.language_combo.setToolTip(text("language", self.language))
        self.package_model.set_language(self.language)
        self.orphan_model.set_language(self.language)
        self.cache_model.set_language(self.language)
        self.detail.set_language(self.language)
        if self.graph is not None:
            self._update_orphan_summary(orphans(self.graph))

    def _scan_cache(self) -> None:
        task = CacheTask()
        self.cache_task = task
        task.signals.completed.connect(self._cache_loaded)
        task.signals.failed.connect(self._cache_failed)
        self.thread_pool.start(task)

    def _cache_loaded(self, entries: tuple[CachedPackage, ...]) -> None:
        self.cache_model.set_entries(entries)
        self.cache_summary.setText(
            text("cache_total", self.language, count=len(entries), size=format_size(cache_total(entries)))
        )

    def _cache_failed(self, error: str) -> None:
        self.cache_summary.setText(error)

    def _request_removal(self) -> None:
        if self.selected_package is None:
            return
        if self.selected_package.name in protected_packages():
            self.statusBar().showMessage(text("protected", self.language))
            return
        self.remove_button.setEnabled(False)
        task = DryRunTask((self.selected_package.name,))
        self.dry_run_task = task
        task.signals.completed.connect(self._show_removal_preview)
        task.signals.failed.connect(self._dry_run_failed)
        self.thread_pool.start(task)

    def _dry_run_failed(self, error: str) -> None:
        self.remove_button.setEnabled(True)
        self.statusBar().showMessage(text("dry_run_failed", self.language, error=error))

    def _show_removal_preview(self, result: DryRunResult) -> None:
        self.remove_button.setEnabled(True)
        dialog = QMessageBox(self)
        dialog.setWindowTitle(text("dry_run", self.language))
        dialog.setText("\n".join(result.targets))
        dialog.setInformativeText(text("confirm_remove", self.language))
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        if dialog.exec() == QMessageBox.StandardButton.Yes:
            task = RemovalTask(result.requested, result)
            self.removal_task = task
            task.signals.completed.connect(lambda _result: self._load())
            task.signals.failed.connect(self._dry_run_failed)
            self.thread_pool.start(task)
