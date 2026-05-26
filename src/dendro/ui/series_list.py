"""series_list.py — Sidebar panel for managing loaded ring-width series.

exports: SeriesListPanel
used_by:
  dendro.ui.main_window → left dock widget
rules:
  - Checkboxes toggle series visibility in SeriesView.
  - Right-click context menu for remove/set-reference/properties.
  - Colour swatch matches the series plot colour.
  - Reacts to SessionManager signals for add/remove/change.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QDockWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QWidget,
    QVBoxLayout,
    QLabel,
    QAbstractItemView,
)

from dendro.resources import CVD_SAFE_PALETTE

if TYPE_CHECKING:
    from dendro.models.session import SessionManager

logger = logging.getLogger(__name__)


def _color_swatch_icon(color_hex: str, size: int = 16) -> QIcon:
    """Create a small square colour swatch icon."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.end()
    return QIcon(pixmap)


class SeriesListPanel(QDockWidget):
    """Dockable sidebar listing all loaded ring-width series.

    Signals:
        visibility_changed(str, bool): Emitted when a series checkbox is
            toggled (series_id, is_visible).
        series_remove_requested(str): Emitted on right-click > Remove.
        set_reference_requested(str): Emitted on right-click > Set as Reference.

    Rules:
        - Automatically updates when SessionManager emits signals.
        - Each row shows: colour swatch, checkbox, ID, year range, ring count.
    """

    visibility_changed = pyqtSignal(str, bool)
    series_remove_requested = pyqtSignal(str)
    set_reference_requested = pyqtSignal(str)
    series_selected = pyqtSignal(str)

    def __init__(self, session: SessionManager, parent=None) -> None:
        super().__init__("Series", parent)
        self._session = session
        self._color_map: dict[str, str] = {}
        self._color_index = 0

        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setMinimumWidth(250)

        # Container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header = QLabel("Loaded Series")
        header.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #d4d4d4; padding: 4px;")
        layout.addWidget(header)

        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Series", "Years", "Rings", "Type"])
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setAlternatingRowColors(True)
        self._tree.setStyleSheet(
            """
            QTreeWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2d2d30;
                border: 1px solid #3c3f41;
                selection-background-color: #0072B2;
            }
            QTreeWidget::item {
                padding: 4px 2px;
            }
            """
        )
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)

        # Column widths
        self._tree.setColumnWidth(0, 100)
        self._tree.setColumnWidth(1, 100)
        self._tree.setColumnWidth(2, 50)
        self._tree.setColumnWidth(3, 60)

        layout.addWidget(self._tree)
        self.setWidget(container)

        # Connect session signals
        self._session.series_added.connect(self._on_series_added)
        self._session.series_removed.connect(self._on_series_removed)
        self._session.series_changed.connect(self._on_series_changed)
        self._session.session_cleared.connect(self._on_session_cleared)

    # ------------------------------------------------------------------ #
    # Tree management
    # ------------------------------------------------------------------ #

    def _assign_color(self, series_id: str) -> str:
        """Assign the next CVD-safe colour to a series."""
        color = CVD_SAFE_PALETTE[self._color_index % len(CVD_SAFE_PALETTE)]
        self._color_map[series_id] = color
        self._color_index += 1
        return color

    def _add_tree_item(self, series_id: str) -> None:
        """Add a tree item for the given series."""
        series = self._session.get_series(series_id)
        color = self._assign_color(series_id)

        item = QTreeWidgetItem()
        item.setData(0, Qt.ItemDataRole.UserRole, series_id)
        item.setCheckState(0, Qt.CheckState.Checked)
        item.setIcon(0, _color_swatch_icon(color))
        item.setText(0, series_id)
        item.setText(1, f"{series.start_year}–{series.end_year}")
        item.setText(2, str(series.ring_count))
        item.setText(3, "Ref" if series.is_reference else "Float")

        # Style reference series differently
        if series.is_reference:
            for col in range(4):
                item.setForeground(col, QColor("#009E73"))

        self._tree.addTopLevelItem(item)

    def _find_item(self, series_id: str) -> QTreeWidgetItem | None:
        """Find a tree item by series_id."""
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == series_id:
                return item
        return None

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    def _show_context_menu(self, pos) -> None:
        """Show right-click context menu."""
        item = self._tree.itemAt(pos)
        if item is None:
            return
        series_id = item.data(0, Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #2d2d30; border: 1px solid #3c3f41; }"
            "QMenu::item { color: #d4d4d4; padding: 6px 20px; }"
            "QMenu::item:selected { background-color: #0072B2; }"
        )

        set_ref_action = menu.addAction("Set as Reference")
        set_ref_action.triggered.connect(
            lambda: self.set_reference_requested.emit(series_id)
        )

        menu.addSeparator()

        remove_action = menu.addAction("Remove Series")
        remove_action.triggered.connect(
            lambda: self.series_remove_requested.emit(series_id)
        )

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------ #
    # Signal handlers
    # ------------------------------------------------------------------ #

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle checkbox state change."""
        if column == 0:
            series_id = item.data(0, Qt.ItemDataRole.UserRole)
            is_visible = item.checkState(0) == Qt.CheckState.Checked
            self.visibility_changed.emit(series_id, is_visible)

    def _on_selection_changed(self) -> None:
        """Handle row selection."""
        selected = self._tree.selectedItems()
        if selected:
            series_id = selected[0].data(0, Qt.ItemDataRole.UserRole)
            self.series_selected.emit(series_id)

    def _on_series_added(self, series_id: str) -> None:
        self._add_tree_item(series_id)

    def _on_series_removed(self, series_id: str) -> None:
        item = self._find_item(series_id)
        if item is not None:
            idx = self._tree.indexOfTopLevelItem(item)
            self._tree.takeTopLevelItem(idx)

    def _on_series_changed(self, series_id: str) -> None:
        item = self._find_item(series_id)
        if item is None:
            return
        series = self._session.get_series(series_id)
        item.setText(1, f"{series.start_year}–{series.end_year}")
        item.setText(2, str(series.ring_count))
        item.setText(3, "Ref" if series.is_reference else "Float")

    def _on_session_cleared(self) -> None:
        self._tree.clear()
        self._color_map.clear()
        self._color_index = 0
