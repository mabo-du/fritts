"""series_view.py — PyQtGraph-based interactive time-series canvas.

exports: SeriesView
used_by:
  dendro.ui.main_window → central widget (upper splitter pane)
rules:
  - Uses PyQtGraph, NEVER Matplotlib, for all rendering.
  - CVD-safe palette + varying line styles for accessibility.
  - Crosshair tracks cursor position showing year and width.
  - Supports dragging floating series along X-axis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QPen, QColor, QFont
from PyQt6.QtWidgets import QMenu

from dendro.resources import CVD_SAFE_PALETTE, LINE_STYLES

if TYPE_CHECKING:
    from dendro.models.session import SessionManager

logger = logging.getLogger(__name__)

# PyQtGraph global config for dark theme
pg.setConfigOptions(
    background=QColor(30, 30, 30),
    foreground=QColor(212, 212, 212),
    antialias=True,
)


class SeriesView(pg.PlotWidget):
    """Interactive ring-width series canvas with zoom, pan, overlay, and drag.

    Signals:
        year_hovered(int): Emitted when the crosshair moves to a new year.
        series_shift_requested(str, int): Emitted when user drags a floating
            series to a new offset (series_id, new_start_year).
        phantom_ring_requested(str, int): Emitted when user requests ring
            insertion at (series_id, year).
        delete_ring_requested(str, int): Emitted when user requests ring
            deletion at (series_id, year).

    Rules:
        - Never mutate series data directly — emit signals for CommandStack.
        - Plot items keyed by series_id for efficient add/remove/update.
        - Uses downsampling for performance on long series.
    """

    year_hovered = pyqtSignal(int)
    series_shift_requested = pyqtSignal(str, int)
    phantom_ring_requested = pyqtSignal(str, int)
    delete_ring_requested = pyqtSignal(str, int)

    def __init__(self, session: SessionManager, parent=None) -> None:
        super().__init__(parent=parent)
        self._session = session
        self._plot_items: dict[str, pg.PlotDataItem] = {}
        self._visible_series: set[str] = set()
        self._color_index = 0
        self._normalize = False
        self._show_indices = False
        self._show_skeleton = False

        # Axis configuration
        self.setLabel("bottom", "Year", units=None)
        self.setLabel("left", "Ring Width", units="mm")
        self.showGrid(x=True, y=True, alpha=0.15)
        self.setMouseEnabled(x=True, y=True)
        self.enableAutoRange(axis="y")

        # Style the axes
        axis_font = QFont("Inter", 10)
        for axis_name in ("bottom", "left"):
            axis = self.getAxis(axis_name)
            axis.setTickFont(axis_font)
            axis.setPen(pg.mkPen(color="#888888", width=1))

        # Crosshair
        self._vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#ffffff", width=1, style=Qt.PenStyle.DotLine),
        )
        self._hline = pg.InfiniteLine(
            angle=0, movable=False,
            pen=pg.mkPen(color="#ffffff", width=1, style=Qt.PenStyle.DotLine),
        )
        self.addItem(self._vline, ignoreBounds=True)
        self.addItem(self._hline, ignoreBounds=True)

        # Crosshair label
        self._cursor_label = pg.TextItem(
            text="", anchor=(0, 1), color="#d4d4d4",
            fill=pg.mkBrush(color=(45, 45, 48, 200)),
        )
        self._cursor_label.setFont(QFont("Inter", 9))
        self.addItem(self._cursor_label, ignoreBounds=True)

        # Connect mouse movement
        self.scene().sigMouseMoved.connect(self._on_mouse_moved)

        # Connect session signals
        self._session.series_added.connect(self._on_series_added)
        self._session.series_removed.connect(self._on_series_removed)
        self._session.series_changed.connect(self._on_series_changed)
        self._session.session_cleared.connect(self._on_session_cleared)

        # Context menu
        self.setMenuEnabled(False)
        self.scene().sigMouseClicked.connect(self._on_mouse_clicked)

    # ------------------------------------------------------------------ #
    # Plot management
    # ------------------------------------------------------------------ #

    def _get_pen(self, index: int) -> QPen:
        """Return a CVD-safe pen with unique colour + line style.

        Rules:
            - Cycles through palette colours, then through line styles.
            - Line width 2px for clarity at all zoom levels.
        """
        color_idx = index % len(CVD_SAFE_PALETTE)
        style_idx = (index // len(CVD_SAFE_PALETTE)) % len(LINE_STYLES)
        pen = QPen(QColor(CVD_SAFE_PALETTE[color_idx]))
        pen.setWidth(2)
        pen.setStyle(LINE_STYLES[style_idx])
        return pen

    def add_series_plot(self, series_id: str) -> None:
        """Add a series to the plot canvas."""
        if series_id in self._plot_items:
            return
        series = self._session.get_series(series_id)
        years = series.years.astype(np.float64)
        
        if self._show_indices and series.indices is not None:
            y_data = series.indices.copy()
        else:
            y_data = series.widths.copy()

        if self._normalize:
            mean = np.nanmean(y_data)
            std = np.nanstd(y_data)
            if std > 0:
                y_data = (y_data - mean) / std

        pen = self._get_pen(self._color_index)
        self._color_index += 1

        if self._show_skeleton:
            from scipy.ndimage import uniform_filter1d
            # Calculate skeleton: (local_mean - width) / local_mean. Scaled 0 to 10.
            # Only plot narrow rings (positive values).
            local_mean = uniform_filter1d(y_data, size=5)
            skeleton_heights = np.clip((local_mean - y_data) / (local_mean + 1e-9), 0, 1) * 10
            
            item = pg.BarGraphItem(
                x=years, height=skeleton_heights, width=0.3,
                pen=pen, brush=pen.color(), name=series_id
            )
        else:
            item = pg.PlotDataItem(
                x=years,
                y=y_data,
                pen=pen,
                name=series_id,
                connect="finite",  # Skip NaN gaps gracefully
                clipToView=True,
                downsample=5,
                downsampleMethod="peak",
                autoDownsample=True,
            )
        self.addItem(item)
        self._plot_items[series_id] = item
        self._visible_series.add(series_id)

    def remove_series_plot(self, series_id: str) -> None:
        """Remove a series from the plot canvas."""
        if series_id in self._plot_items:
            self.removeItem(self._plot_items[series_id])
            del self._plot_items[series_id]
            self._visible_series.discard(series_id)

    def update_series_plot(self, series_id: str) -> None:
        """Refresh the data for a specific series (e.g., after shift/edit)."""
        if series_id not in self._plot_items:
            return
        series = self._session.get_series(series_id)
        years = series.years.astype(np.float64)
        
        if self._show_indices and series.indices is not None:
            y_data = series.indices.copy()
        else:
            y_data = series.widths.copy()

        if self._normalize:
            mean = np.nanmean(y_data)
            std = np.nanstd(y_data)
            if std > 0:
                y_data = (y_data - mean) / std

        if self._show_skeleton:
            from scipy.ndimage import uniform_filter1d
            local_mean = uniform_filter1d(y_data, size=5)
            skeleton_heights = np.clip((local_mean - y_data) / (local_mean + 1e-9), 0, 1) * 10
            
            # If current item is not a BarGraphItem, recreate it
            if not isinstance(self._plot_items[series_id], pg.BarGraphItem):
                self.remove_series_plot(series_id)
                self.add_series_plot(series_id)
                return
            self._plot_items[series_id].setOpts(x=years, height=skeleton_heights)
        else:
            if not isinstance(self._plot_items[series_id], pg.PlotDataItem):
                self.remove_series_plot(series_id)
                self.add_series_plot(series_id)
                return
            self._plot_items[series_id].setData(x=years, y=y_data)

    def set_series_visible(self, series_id: str, visible: bool) -> None:
        """Toggle visibility of a specific series."""
        if series_id in self._plot_items:
            self._plot_items[series_id].setVisible(visible)
            if visible:
                self._visible_series.add(series_id)
            else:
                self._visible_series.discard(series_id)

    def set_normalize(self, normalize: bool) -> None:
        """Toggle Z-score normalization for all series."""
        self._normalize = normalize
        for series_id in list(self._plot_items.keys()):
            self.update_series_plot(series_id)
            
    def set_show_indices(self, show: bool) -> None:
        """Toggle viewing standardized RWI vs raw widths."""
        self._show_indices = show
        if show:
            self.setLabel("left", "Ring Width Index", units="RWI")
        else:
            self.setLabel("left", "Ring Width", units="mm")
            
        if not self._show_skeleton:
            for series_id in list(self._plot_items.keys()):
                self.update_series_plot(series_id)
            self.autoRange()

    def set_show_skeleton(self, show: bool) -> None:
        """Toggle Skeleton Plot mode (visualizing narrow rings only)."""
        self._show_skeleton = show
        if show:
            self.setLabel("left", "Relative Narrowness", units="Score")
        else:
            if self._show_indices:
                self.setLabel("left", "Ring Width Index", units="RWI")
            else:
                self.setLabel("left", "Ring Width", units="mm")
                
        for series_id in list(self._plot_items.keys()):
            self.update_series_plot(series_id)
        self.autoRange()

    def refresh_all(self) -> None:
        """Rebuild all plots from session data."""
        # Remove all existing
        for item in self._plot_items.values():
            self.removeItem(item)
        self._plot_items.clear()
        self._visible_series.clear()
        self._color_index = 0
        # Re-add
        for series_id in self._session.series_ids:
            self.add_series_plot(series_id)

    # ------------------------------------------------------------------ #
    # Crosshair & cursor
    # ------------------------------------------------------------------ #

    def _on_mouse_moved(self, pos: QPointF) -> None:
        """Update crosshair and cursor label on mouse move."""
        if not self.sceneBoundingRect().contains(pos):
            return
        mouse_point = self.plotItem.vb.mapSceneToView(pos)
        year = int(round(mouse_point.x()))
        width = mouse_point.y()

        self._vline.setPos(mouse_point.x())
        self._hline.setPos(mouse_point.y())

        self._cursor_label.setText(f"Year: {year}  Width: {width:.2f} mm")
        self._cursor_label.setPos(mouse_point.x(), mouse_point.y())

        self.year_hovered.emit(year)

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #

    def _on_mouse_clicked(self, evt) -> None:
        """Show context menu on right-click."""
        if evt.button() != Qt.MouseButton.RightButton:
            return
        pos = evt.scenePos()
        if not self.sceneBoundingRect().contains(pos):
            return

        mouse_point = self.plotItem.vb.mapSceneToView(pos)
        year = int(round(mouse_point.x()))

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #2d2d30; border: 1px solid #3c3f41; }"
            "QMenu::item { color: #d4d4d4; padding: 6px 20px; }"
            "QMenu::item:selected { background-color: #0072B2; }"
        )

        # Find which series are at this year
        for series_id in self._visible_series:
            series = self._session.get_series(series_id)
            if series.start_year <= year <= series.end_year:
                sub_menu = menu.addMenu(f"Series: {series_id}")
                insert_action = sub_menu.addAction(f"Insert phantom ring at {year}")
                insert_action.triggered.connect(
                    lambda checked, sid=series_id, y=year:
                        self.phantom_ring_requested.emit(sid, y)
                )
                delete_action = sub_menu.addAction(f"Delete ring at {year}")
                delete_action.triggered.connect(
                    lambda checked, sid=series_id, y=year:
                        self.delete_ring_requested.emit(sid, y)
                )

        if menu.actions():
            menu.exec(evt.screenPos().toPoint())

    # ------------------------------------------------------------------ #
    # Session signal handlers
    # ------------------------------------------------------------------ #

    def _on_series_added(self, series_id: str) -> None:
        self.add_series_plot(series_id)

    def _on_series_removed(self, series_id: str) -> None:
        self.remove_series_plot(series_id)

    def _on_series_changed(self, series_id: str) -> None:
        self.update_series_plot(series_id)

    def _on_session_cleared(self) -> None:
        self.refresh_all()
