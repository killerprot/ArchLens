"""Main ArchLens window."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt, QThreadPool
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
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

from archlens.app.cache import CacheCleanupTask, CacheTask
from archlens.app.removal import DryRunTask, RemovalTask
from archlens.app.workers import LoadPackagesTask, RemovalEstimateTask
from archlens.core.analysis import orphans
from archlens.core.cache_analysis import CachedPackage, cache_total
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.core.protection import protected_packages
from archlens.core.report import write_report
from archlens.infra.config import load_config
from archlens.infra.pacman_cli import DryRunResult
from archlens.strings import LANGUAGES, text
from archlens.ui.cache_view import CacheTableModel
from archlens.ui.graph_view import GraphView
from archlens.ui.package_detail import PackageDetail
from archlens.ui.package_table import PackageFilterModel, PackageTableModel, format_size


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "en"
        self.config = load_config()
        self.protected_names = protected_packages(set(self.config.protected))
        self.setWindowTitle(text("app_title"))
        self.resize(1100, 700)
        self.setStyleSheet(
            """
            QMainWindow, QWidget#appRoot { background: palette(window); }
            QWidget#topBar { background: palette(base); border: 1px solid palette(mid); border-radius: 10px; }
            QLineEdit, QComboBox {
                min-height: 30px;
                padding: 2px 10px;
                border: 1px solid palette(mid);
                border-radius: 7px;
                background: palette(base);
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid palette(highlight); padding: 1px 9px; }
            QPushButton {
                min-height: 30px;
                padding: 2px 14px;
                border: 1px solid palette(mid);
                border-radius: 7px;
                background: palette(button);
            }
            QPushButton:hover { border-color: palette(highlight); }
            QPushButton:disabled { color: palette(mid); }
            QPushButton#removeButton { background: palette(alternate-base); }
            QTableView {
                border: 1px solid palette(mid);
                border-radius: 9px;
                alternate-background-color: palette(alternate-base);
                gridline-color: palette(midlight);
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
            }
            QHeaderView::section {
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid palette(mid);
                background: palette(alternate-base);
                font-weight: 600;
            }
            QTabWidget::pane { border: none; }
            QTabBar::tab { padding: 10px 18px; margin-right: 3px; border-radius: 7px; }
            QTabBar::tab:selected { background: palette(highlight); color: palette(highlighted-text); }
            QTabBar::tab:hover:!selected { background: palette(alternate-base); }
            QSplitter::handle { background: palette(mid); }
            QLabel#summaryLabel { padding: 8px 10px; color: palette(text); }
            QLabel#detailPanel { padding: 0; border: 1px solid palette(mid); border-radius: 9px; background: palette(base); }
            QLabel#detailTitle { font-size: 15px; font-weight: 700; }
            QLabel#detailItem { padding: 5px 0; }
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
        self.cache_cleanup_task: CacheCleanupTask | None = None
        self.estimate_task: RemovalEstimateTask | None = None
        self.estimate_statuses: dict[str, str] = {}
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
        self.graph_view = GraphView()
        self.graph_view.node_selected.connect(self._graph_node_selected)
        self.cache_proxy = QSortFilterProxyModel()
        self.cache_proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.cache_proxy.setFilterKeyColumn(0)
        self.cache_proxy.setSourceModel(self.cache_model)
        self._build_ui()
        self.statusBar().showMessage(text("loading", self.language))
        self._load()
        self._scan_cache()

    def _make_table(self, model: PackageFilterModel) -> QTableView:
        view = QTableView()
        view.setObjectName("packageTable")
        view.setModel(model)
        view.setSortingEnabled(True)
        view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        view.setShowGrid(False)
        view.setAlternatingRowColors(True)
        view.setWordWrap(False)
        view.verticalHeader().setVisible(False)
        view.horizontalHeader().setStretchLastSection(True)
        view.clicked.connect(lambda index, proxy=model: self._package_selected(index, proxy))
        return view

    def _build_ui(self) -> None:
        packages_page = QWidget()
        packages_layout = QVBoxLayout(packages_page)
        packages_layout.setContentsMargins(12, 10, 12, 12)
        packages_layout.setSpacing(10)
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
        orphan_layout.setContentsMargins(12, 10, 12, 12)
        orphan_layout.setSpacing(10)
        self.orphan_search = QLineEdit()
        self.orphan_search.textChanged.connect(self.orphan_proxy.setFilterFixedString)
        orphan_layout.addWidget(self.orphan_search)
        self.orphan_summary = QLabel()
        self.orphan_summary.setObjectName("summaryLabel")
        orphan_layout.addWidget(self.orphan_summary)
        orphan_layout.addWidget(self.orphan_view)
        self.tabs.addTab(orphan_page, "")

        cache_page = QWidget()
        cache_layout = QVBoxLayout(cache_page)
        cache_layout.setContentsMargins(12, 10, 12, 12)
        cache_layout.setSpacing(10)
        self.cache_search = QLineEdit()
        self.cache_search.textChanged.connect(self.cache_proxy.setFilterFixedString)
        cache_layout.addWidget(self.cache_search)
        self.cache_summary = QLabel()
        self.cache_summary.setObjectName("summaryLabel")
        self.cache_cleanup_button = QPushButton()
        self.cache_cleanup_button.clicked.connect(self._request_cache_cleanup)
        self.cache_view = QTableView()
        self.cache_view.setModel(self.cache_proxy)
        self.cache_view.setShowGrid(False)
        self.cache_view.setAlternatingRowColors(True)
        self.cache_view.verticalHeader().setVisible(False)
        self.cache_view.horizontalHeader().setStretchLastSection(True)
        cache_layout.addWidget(self.cache_summary)
        cache_layout.addWidget(self.cache_cleanup_button)
        cache_layout.addWidget(self.cache_view)
        self.tabs.addTab(cache_page, "")

        graph_page = QWidget()
        graph_layout = QVBoxLayout(graph_page)
        graph_layout.setContentsMargins(12, 10, 12, 12)
        graph_layout.setSpacing(10)
        self.graph_hint = QLabel()
        self.graph_hint.setObjectName("summaryLabel")
        graph_layout.addWidget(self.graph_hint)
        graph_layout.addWidget(self.graph_view)
        self.tabs.addTab(graph_page, "")

        toolbar = QWidget()
        toolbar.setObjectName("topBar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 6, 10, 6)
        toolbar_layout.addStretch()
        self.export_button = QPushButton()
        self.export_button.clicked.connect(self._export_report)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.language_combo)
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 10, 12, 12)
        root_layout.setSpacing(10)
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
        self.orphan_model.set_optional_names(
            {item.package.name for item in orphan_items if item.optionally_required}
        )
        self.package_view.resizeColumnsToContents()
        self.orphan_view.resizeColumnsToContents()
        self._update_orphan_summary(orphan_items)
        self.statusBar().showMessage(text("packages_loaded", self.language, count=len(packages)))
        task = RemovalEstimateTask(graph, set(self.config.protected))
        self.estimate_task = task
        task.signals.completed.connect(self._estimates_loaded)
        task.signals.failed.connect(self._load_failed)
        self.thread_pool.start(task)

    def _estimates_loaded(self, estimates: dict[str, int], statuses: dict[str, str]) -> None:
        self.estimate_statuses = statuses
        self.package_model.set_estimates(estimates, statuses)
        self.orphan_model.set_estimates(estimates, statuses)
        if self.graph is not None:
            self._update_orphan_summary(orphans(self.graph))

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
            self.remove_button.setEnabled(package.name not in self.protected_names)
            self.detail.show_package(package, self.graph)
            self.graph_view.show_package(package, self.graph)

    def _graph_node_selected(self, package_name: str) -> None:
        if self.graph is None or package_name not in self.graph.by_name:
            return
        package = self.graph.by_name[package_name]
        self.selected_package = package
        self.remove_button.setEnabled(package.name not in self.protected_names)
        self.detail.show_package(package, self.graph)
        self.graph_view.show_package(package, self.graph)

    def _language_changed(self, index: int) -> None:
        self.language = self.language_combo.itemData(index)
        self._retranslate()

    def _update_orphan_summary(self, orphan_items) -> None:
        optional = sum(1 for item in orphan_items if item.optionally_required)
        safe_items = [
            item
            for item in orphan_items
            if not item.optionally_required and item.package.name not in self.estimate_statuses
        ]
        total = sum(item.package.installed_size for item in safe_items)
        self.orphan_summary.setText(
            text(
                "orphans_total",
                self.language,
                count=len(orphan_items),
                optional=optional,
                safe=len(safe_items),
                size=format_size(total),
            )
        )

    def _retranslate(self) -> None:
        self.setWindowTitle(text("app_title", self.language))
        self.tabs.setTabText(0, text("tab_packages", self.language))
        self.tabs.setTabText(1, text("tab_orphans", self.language))
        self.tabs.setTabText(2, text("tab_cache", self.language))
        self.tabs.setTabText(3, text("tab_graph", self.language))
        self.search.setPlaceholderText(text("search", self.language))
        self.orphan_search.setPlaceholderText(text("search", self.language))
        self.cache_search.setPlaceholderText(text("search", self.language))
        self.remove_button.setText(text("remove_selected", self.language))
        self.export_button.setText(text("export", self.language))
        self.cache_cleanup_button.setText(text("clear_cache", self.language))
        self.graph_hint.setText(text("graph_hint", self.language))
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

    def _request_cache_cleanup(self) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(text("cache_cleanup", self.language))
        dialog.setText(text("confirm_cache_cleanup", self.language))
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        if dialog.exec() != QMessageBox.StandardButton.Yes:
            return
        self.cache_cleanup_button.setEnabled(False)
        task = CacheCleanupTask(keep_versions=self.config.keep_versions)
        self.cache_cleanup_task = task
        task.signals.completed.connect(self._cache_cleanup_done)
        task.signals.failed.connect(self._cache_cleanup_failed)
        self.thread_pool.start(task)

    def _cache_cleanup_done(self, _result) -> None:
        self.cache_cleanup_button.setEnabled(True)
        self._scan_cache()

    def _cache_cleanup_failed(self, error: str) -> None:
        self.cache_cleanup_button.setEnabled(True)
        self.statusBar().showMessage(error)

    def _export_report(self) -> None:
        if self.graph is None:
            return
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            text("export", self.language),
            "archlens-report.json",
            text("export_filter", self.language),
        )
        if not path:
            return
        write_report(path, self.graph, self.package_model.freed, self.estimate_statuses)
        self.statusBar().showMessage(text("exported", self.language, path=path))

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
