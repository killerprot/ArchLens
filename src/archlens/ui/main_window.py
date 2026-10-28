"""Main ArchLens window."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSortFilterProxyModel, Qt, QThreadPool
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabBar,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from archlens.app.cache import CacheCleanupTask, CacheTask
from archlens.app.removal import DryRunTask, RemovalTask
from archlens.app.workers import LoadPackagesTask, RemovalEstimateTask
from archlens.core.cache_analysis import CachedPackage, cache_total
from archlens.core.graph import DependencyGraph
from archlens.core.models import Package
from archlens.core.protection import protected_packages
from archlens.core.report import write_report
from archlens.core.usage import UsageStatus, compute_usage, orphans
from archlens.infra.config import load_config
from archlens.infra.pacman_cli import DryRunResult
from archlens.strings import LANGUAGES, text
from archlens.ui.cache_view import CacheTableModel
from archlens.ui.graph_view import GraphView
from archlens.ui.package_detail import PackageDetail
from archlens.ui.package_table import PackageFilterModel, PackageTableModel, format_size


class AnimatedTabBar(QTabBar):
    """Move a small accent block between tabs when the current page changes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("mainTabBar")
        self.indicator = QFrame(self)
        self.indicator.setObjectName("tabIndicator")
        self.indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._indicator_animation: QPropertyAnimation | None = None
        self.currentChanged.connect(self._move_indicator)

    def _indicator_rect(self, index: int):
        rect = self.tabRect(index)
        return rect.adjusted(10, rect.height() - 4, -10, 0)

    def _move_indicator(self, index: int) -> None:
        if index < 0:
            self.indicator.hide()
            return
        target = self._indicator_rect(index)
        if not self.indicator.isVisible() or not self.isVisible():
            self.indicator.setGeometry(target)
            self.indicator.show()
            return
        animation = QPropertyAnimation(self.indicator, b"geometry", self)
        animation.setDuration(180)
        animation.setStartValue(self.indicator.geometry())
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._indicator_animation = animation
        animation.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.currentIndex() >= 0:
            self.indicator.setGeometry(self._indicator_rect(self.currentIndex()))


class AnimatedSelectionTable(QTableView):
    """Table view with a lightweight animated outline around the current row."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.selection_indicator = QFrame(self.viewport())
        self.selection_indicator.setObjectName("selectionIndicator")
        self.selection_indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.selection_indicator.hide()
        self._selection_animation: QPropertyAnimation | None = None

    def setModel(self, model) -> None:
        super().setModel(model)
        if self.selectionModel() is not None:
            self.selectionModel().currentChanged.connect(self._move_selection_indicator)

    def _move_selection_indicator(self, current, _previous) -> None:
        if not current.isValid():
            self.selection_indicator.hide()
            return
        rect = self.visualRect(current).adjusted(2, 1, -2, -1)
        if not rect.isValid() or rect.height() <= 0:
            self.selection_indicator.hide()
            return
        if not self.selection_indicator.isVisible():
            self.selection_indicator.setGeometry(rect)
            self.selection_indicator.show()
            return
        animation = QPropertyAnimation(self.selection_indicator, b"geometry", self)
        animation.setDuration(150)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setStartValue(self.selection_indicator.geometry())
        animation.setEndValue(rect)
        self._selection_animation = animation
        animation.start()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        current = self.currentIndex()
        if current.isValid() and self.selection_indicator.isVisible():
            self.selection_indicator.setGeometry(self.visualRect(current).adjusted(2, 1, -2, -1))


class AnimatedTabWidget(QTabWidget):
    """Fade the newly selected page into view without replacing Qt's tab behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.setTabBar(AnimatedTabBar())
        self._page_animation: QPropertyAnimation | None = None
        self.currentChanged.connect(self._animate_current_page)

    def _animate_current_page(self, index: int) -> None:
        if not self.isVisible() or index < 0:
            return
        page = self.widget(index)
        if page is None:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        animation = QPropertyAnimation(effect, b"opacity", self)
        animation.setDuration(180)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: page.setGraphicsEffect(None))
        self._page_animation = animation
        animation.start()


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
            QMainWindow, QWidget#appRoot { background: palette(window); color: palette(text); }
            QWidget#topBar { background: #20252e; border: 1px solid #3b424f; border-radius: 12px; }
            QLineEdit, QComboBox {
                min-height: 30px;
                padding: 2px 10px;
                border: 1px solid #3b424f;
                border-radius: 9px;
                background: #171b22;
                color: #e7eaf0;
            }
            QLineEdit:focus, QComboBox:focus { border: 2px solid palette(highlight); padding: 1px 9px; }
            QComboBox#languageCombo { min-width: 112px; }
            QComboBox#languageCombo QAbstractItemView {
                min-width: 112px;
                padding: 5px;
                border: 1px solid #3b424f;
                border-radius: 9px;
                background: #20252e;
                color: #e7eaf0;
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
            }
            QPushButton {
                min-height: 30px;
                padding: 2px 14px;
                border: 1px solid #3b424f;
                border-radius: 9px;
                background: #2a303b;
                color: #e7eaf0;
            }
            QPushButton:hover { border-color: palette(highlight); background: #323947; }
            QPushButton:disabled { color: #737b89; }
            QPushButton#removeButton { background: #272d38; }
            QTableView {
                border: 1px solid #3b424f;
                border-radius: 11px;
                background: #171b22;
                alternate-background-color: #1d222b;
                gridline-color: #292f39;
                selection-background-color: palette(highlight);
                selection-color: palette(highlighted-text);
            }
            QScrollBar:vertical, QScrollBar:horizontal { background: transparent; border: none; margin: 4px; }
            QScrollBar:vertical { width: 10px; }
            QScrollBar:horizontal { height: 10px; }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                min-height: 24px;
                min-width: 24px;
                border-radius: 5px;
                background: #454d5c;
            }
            QScrollBar::handle:hover { background: #596477; }
            QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
            QHeaderView::section {
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #3b424f;
                background: #20252e;
                font-weight: 600;
            }
            QTabWidget::pane { border: none; }
            QTabBar#mainTabBar { background: transparent; }
            QTabBar::tab { padding: 10px 18px; margin-right: 3px; border-radius: 7px; }
            QTabBar::tab:selected { background: palette(highlight); color: palette(highlighted-text); }
            QTabBar::tab:hover:!selected { background: palette(alternate-base); }
            QFrame#tabIndicator { background: palette(highlight); border-radius: 2px; }
            QFrame#selectionIndicator { border: 2px solid palette(highlight); border-radius: 6px; background: transparent; }
            QSplitter::handle { background: #3b424f; }
            QLabel#summaryLabel { padding: 8px 10px; color: palette(text); }
            QWidget#detailPanel { padding: 0; border: 1px solid #3b424f; border-radius: 11px; background: #171b22; }
            QLabel#detailTitle { font-size: 15px; font-weight: 700; }
            QLabel#detailItem { padding: 5px 0; }
            """
        )
        self._apply_dark_palette()
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
        self.tabs = AnimatedTabWidget()
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("languageCombo")
        self.language_combo.setView(QListView())
        self.language_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.language_combo.view().setMinimumWidth(130)
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
        self.orphan_detail = PackageDetail()
        self.orphan_detail.setObjectName("detailPanel")
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
        view = AnimatedSelectionTable()
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
        self.orphan_mode = QComboBox()
        self.orphan_mode.currentIndexChanged.connect(self._orphan_mode_changed)
        orphan_layout.addWidget(self.orphan_mode)
        orphan_layout.addWidget(self.orphan_search)
        self.orphan_summary = QLabel()
        self.orphan_summary.setObjectName("summaryLabel")
        self.orphan_summary.setFixedHeight(36)
        orphan_layout.addWidget(self.orphan_summary)
        orphan_splitter = QSplitter()
        orphan_splitter.addWidget(self.orphan_view)
        orphan_splitter.addWidget(self.orphan_detail)
        orphan_splitter.setStretchFactor(0, 3)
        orphan_splitter.setStretchFactor(1, 2)
        orphan_layout.addWidget(orphan_splitter)
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
        self.cache_summary.setFixedHeight(36)
        self.cache_cleanup_button = QPushButton()
        self.cache_cleanup_button.clicked.connect(self._request_cache_cleanup)
        self.cache_view = AnimatedSelectionTable()
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
        self.graph_hint.setFixedHeight(36)
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

    def _apply_dark_palette(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#171b22"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#171b22"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1d222b"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#2a303b"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e7eaf0"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e7eaf0"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e7eaf0"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#368bd1"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Mid, QColor("#3b424f"))
        palette.setColor(QPalette.ColorRole.Midlight, QColor("#454d5c"))
        QApplication.instance().setPalette(palette)
        self.setPalette(palette)

    def _load(self) -> None:
        task = LoadPackagesTask()
        self.load_task = task
        task.signals.loaded.connect(self._loaded)
        task.signals.failed.connect(self._load_failed)
        self.thread_pool.start(task)

    def _loaded(self, packages: tuple[Package, ...], graph: DependencyGraph) -> None:
        self.packages = packages
        self.graph = graph
        self.usage = compute_usage(graph)
        self.package_model.set_packages(packages)
        self.orphan_names = set(orphans(graph))
        self.optional_only_names = {
            name for name, item in self.usage.items() if item.status is UsageStatus.OPTIONAL_ONLY
        }
        self._refresh_orphan_mode()
        self.orphan_model.set_optional_names(set())
        self.package_view.resizeColumnsToContents()
        self.orphan_view.resizeColumnsToContents()
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
            self._update_orphan_summary(tuple(p for p in self.graph.packages if self.usage[p.name].status is UsageStatus.ORPHAN))

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
            detail = self.orphan_detail if proxy is self.orphan_proxy else self.detail
            detail.show_package(package, self.graph)
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
        optional = 0
        safe_items = [
            item
            for item in orphan_items
            if item.name not in self.estimate_statuses
        ]
        total = sum(item.installed_size for item in safe_items)
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

    def _orphan_mode_changed(self, _index: int) -> None:
        if self.graph is not None:
            self._refresh_orphan_mode()

    def _refresh_orphan_mode(self) -> None:
        names = self.orphan_names if self.orphan_mode.currentIndex() == 0 else self.optional_only_names
        items = tuple(package for package in self.graph.packages if package.name in names)
        self.orphan_model.set_packages(items)
        self.orphan_view.resizeColumnsToContents()
        self._update_orphan_summary(items)

    def _retranslate(self) -> None:
        self.setWindowTitle(text("app_title", self.language))
        self.tabs.setTabText(0, text("tab_packages", self.language))
        self.tabs.setTabText(1, text("tab_orphans", self.language))
        self.tabs.setTabText(2, text("tab_cache", self.language))
        self.tabs.setTabText(3, text("tab_graph", self.language))
        self.search.setPlaceholderText(text("search", self.language))
        self.orphan_search.setPlaceholderText(text("search", self.language))
        self.orphan_mode.clear()
        self.orphan_mode.addItems([
            text("orphan_mode_strict", self.language),
            text("orphan_mode_optional", self.language),
        ])
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
        self.orphan_detail.set_language(self.language)
        if self.graph is not None:
            self._update_orphan_summary(tuple(
                p for p in self.graph.packages
                if self.usage[p.name].status is UsageStatus.ORPHAN
            ))

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
