"""chronology_builder.py — Interactive Chronology Builder panel.

exports: ChronologyBuilderDock
used_by:
  dendro.ui.main_window -> Analysis menu
rules:
  - Update EPS and Rbar dynamically when items are toggled.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QFormLayout,
    QGroupBox,
    QMessageBox,
)

if TYPE_CHECKING:
    from dendro.models.session import SessionManager

logger = logging.getLogger(__name__)


class ChronologyBuilderDock(QDockWidget):
    """A dockable panel for interactive chronology building."""

    def __init__(self, session: "SessionManager", parent=None) -> None:
        super().__init__("Interactive Chronology Builder", parent)
        self._session = session
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        # Connect session updates
        self._session.series_added.connect(self._refresh_list)
        self._session.series_removed.connect(self._refresh_list)
        self._session.session_cleared.connect(self._refresh_list)

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Series selection list
        self._list_widget = QListWidget()
        self._list_widget.itemChanged.connect(self._on_item_toggled)
        layout.addWidget(QLabel("Select series to include:"))
        layout.addWidget(self._list_widget)

        # Metrics group
        metrics_group = QGroupBox("Chronology Quality Metrics")
        metrics_layout = QFormLayout(metrics_group)
        
        self._lbl_n = QLabel("0")
        self._lbl_rbar = QLabel("0.000")
        self._lbl_eps = QLabel("0.000")
        
        metrics_layout.addRow("Trees (N):", self._lbl_n)
        metrics_layout.addRow("R-bar:", self._lbl_rbar)
        metrics_layout.addRow("EPS:", self._lbl_eps)
        layout.addWidget(metrics_group)

        # Build button
        self._build_btn = QPushButton("Build Master Chronology")
        self._build_btn.clicked.connect(self._on_build_clicked)
        layout.addWidget(self._build_btn)

        self.setWidget(widget)

    def _refresh_list(self) -> None:
        """Repopulate the list of series."""
        self._list_widget.blockSignals(True)
        self._list_widget.clear()

        for sid in self._session.series_ids:
            s = self._session.get_series(sid)
            if not s.is_reference:
                item = QListWidgetItem(sid)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self._list_widget.addItem(item)
                
        self._list_widget.blockSignals(False)
        self._update_metrics()

    def _on_item_toggled(self, item: QListWidgetItem) -> None:
        self._update_metrics()

    def _get_selected_series(self) -> list:
        selected = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(self._session.get_series(item.text()))
        return selected

    def _update_metrics(self) -> None:
        from dendro.stats.chronology import calculate_rbar, calculate_eps
        
        selected = self._get_selected_series()
        n = len(selected)
        self._lbl_n.setText(str(n))
        
        if n < 2:
            self._lbl_rbar.setText("N/A")
            self._lbl_eps.setText("N/A")
            # Clear style
            self._lbl_eps.setStyleSheet("")
            self._build_btn.setEnabled(n > 0)
            return

        rbar = calculate_rbar(selected)
        eps = calculate_eps(n, rbar)

        self._lbl_rbar.setText(f"{rbar:.3f}")
        self._lbl_eps.setText(f"{eps:.3f}")

        # Color code EPS (>= 0.85 is generally considered good)
        if eps >= 0.85:
            self._lbl_eps.setStyleSheet("color: #4CAF50; font-weight: bold;") # Green
        else:
            self._lbl_eps.setStyleSheet("color: #F44336; font-weight: bold;") # Red

        self._build_btn.setEnabled(True)

    def _on_build_clicked(self) -> None:
        selected = self._get_selected_series()
        if not selected:
            return
            
        from dendro.stats.chronology import build_chronology
        try:
            chronology, _ = build_chronology(selected, method="robust_mean")
            self._session.add_series(chronology)
            QMessageBox.information(self, "Success", "Master Chronology generated and added to workspace.")
        except Exception as e:
            logger.exception("Failed to build chronology")
            QMessageBox.critical(self, "Error", f"Failed to build chronology:\n\n{e}")
