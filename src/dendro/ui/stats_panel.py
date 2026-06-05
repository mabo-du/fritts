"""stats_panel.py — Cross-dating results panel with score plot and ranked table.

exports: StatsPanel
used_by:
  dendro.ui.main_window → lower splitter pane
rules:
  - Contains two sub-views: match score plot + results table.
  - Clicking a row in the table snaps the floating series to that offset.
  - Auto-clears when session changes.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QHeaderView,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StatsPanel(QWidget):
    """Cross-dating results panel.

    Signals:
        offset_selected(int): Emitted when user clicks a row, providing
            the proposed start year for the floating series.

    Rules:
        - Results are displayed after crossdate_sliding() completes.
        - Table shows top 10 matches sorted by t_BP descending.
        - Score plot shows t_BP across all offset positions.
    """

    offset_selected = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results_df: pd.DataFrame | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("Cross-Dating Results")
        header.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        header.setStyleSheet("color: #d4d4d4; padding: 6px;")
        layout.addWidget(header)

        # Splitter: score plot (left) + table (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Score plot
        self._plot = pg.PlotWidget()
        self._plot.setLabel("bottom", "Proposed Start Year")
        self._plot.setLabel("left", "t-value (BP)")
        self._plot.showGrid(x=True, y=True, alpha=0.15)
        self._plot.setMinimumWidth(300)

        # Threshold line at t=3.5
        threshold_line = pg.InfiniteLine(
            pos=3.5,
            angle=0,
            pen=pg.mkPen(color="#D55E00", width=1, style=Qt.PenStyle.DashLine),
            label="t=3.5",
            labelOpts={"color": "#D55E00", "position": 0.95},
        )
        self._plot.addItem(threshold_line)

        self._score_curve = self._plot.plot(
            pen=pg.mkPen(color="#0072B2", width=2),
            name="t_BP",
        )
        self._peak_scatter = pg.ScatterPlotItem(
            size=8,
            pen=pg.mkPen(color="#D55E00", width=1),
            brush=pg.mkBrush(color="#D55E00"),
        )
        self._plot.addItem(self._peak_scatter)
        splitter.addWidget(self._plot)

        # Results table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["Start Year", "t_BP", "t_Ho", "GLK", "P-value", "Overlap"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            """
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2d2d30;
                selection-background-color: #0072B2;
                gridline-color: #3c3f41;
            }
            """
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setMinimumWidth(400)
        self._table.cellClicked.connect(self._on_row_clicked)
        splitter.addWidget(self._table)

        splitter.setSizes([400, 400])

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def display_results(self, results_df: pd.DataFrame) -> None:
        """Display cross-dating results.

        Args:
            results_df: DataFrame indexed by proposed start year with columns
                        t_bp, t_ho, glk, z_score, p_value, overlap.

        Rules:
            - Score plot shows t_BP vs. start year.
            - Table shows top 10 matches sorted by t_BP descending.
            - Peaks above t=3.5 are highlighted with scatter markers.
        """
        self._results_df = results_df

        if results_df.empty:
            self.clear_results()
            return

        # Update score plot
        years = results_df.index.to_numpy(dtype=np.float64)
        t_bp_values = results_df["t_bp"].to_numpy(dtype=np.float64)
        self._score_curve.setData(x=years, y=t_bp_values)

        # Highlight peaks above threshold
        mask = t_bp_values >= 3.5
        if mask.any():
            self._peak_scatter.setData(
                x=years[mask], y=t_bp_values[mask]
            )
        else:
            self._peak_scatter.setData(x=[], y=[])

        # Update table with top 10
        top = results_df.nlargest(10, "t_bp")
        self._table.setRowCount(len(top))
        for row_idx, (start_year, row) in enumerate(top.iterrows()):
            items = [
                (str(int(start_year)), Qt.AlignmentFlag.AlignCenter),
                (f"{row['t_bp']:.2f}", Qt.AlignmentFlag.AlignRight),
                (f"{row['t_ho']:.2f}", Qt.AlignmentFlag.AlignRight),
                (f"{row['glk']:.3f}", Qt.AlignmentFlag.AlignRight),
                (f"{row['p_value']:.4f}", Qt.AlignmentFlag.AlignRight),
                (str(int(row['overlap'])), Qt.AlignmentFlag.AlignCenter),
            ]
            for col_idx, (text, alignment) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Highlight strong matches
                if col_idx == 1 and row["t_bp"] >= 5.0:
                    item.setForeground(QColor("#009E73"))
                elif col_idx == 1 and row["t_bp"] >= 3.5:
                    item.setForeground(QColor("#E69F00"))
                self._table.setItem(row_idx, col_idx, item)

    def clear_results(self) -> None:
        """Clear all results from the panel."""
        self._results_df = None
        self._score_curve.setData(x=[], y=[])
        self._peak_scatter.setData(x=[], y=[])
        self._table.setRowCount(0)

    # ------------------------------------------------------------------ #
    # Slot handlers
    # ------------------------------------------------------------------ #

    def _on_row_clicked(self, row: int, _col: int) -> None:
        """Handle click on a results table row."""
        item = self._table.item(row, 0)
        if item is not None:
            start_year = int(item.text())
            self.offset_selected.emit(start_year)
