"""image_view.py — Interactive canvas for measuring tree rings from scans.

exports: ImageMeasurementView
used_by: dendro.ui.main_window
rules:
  - Uses PyQtGraph ImageItem for high-performance rendering of gigapixel images.
  - Allows dropping markers to define ring boundaries.
  - Extracts millimeter distances based on DPI.
"""

from __future__ import annotations

import logging
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QInputDialog,
    QMessageBox,
)

from dendro.models.series import RingWidthSeries

class PithEstimatorItem(pg.GraphicsObject):
    """Custom concentric circle overlay for estimating distance to pith."""
    
    def __init__(self, radius: float = 200.0) -> None:
        super().__init__()
        self.radius = radius
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges)

    def boundingRect(self):
        from PyQt6.QtCore import QRectF
        return QRectF(-self.radius, -self.radius, 2*self.radius, 2*self.radius)

    def paint(self, p, *args):
        from PyQt6.QtCore import QRectF, Qt
        p.setRenderHint(p.RenderHint.Antialiasing)
        p.setPen(pg.mkPen(color="#00FF00", width=2, style=Qt.PenStyle.DashLine))
        
        # Draw concentric circles
        for r in np.linspace(20, self.radius, 6):
            p.drawEllipse(QRectF(-r, -r, 2*r, 2*r))
            
        # Draw crosshair
        p.drawLine(int(-self.radius), 0, int(self.radius), 0)
        p.drawLine(0, int(-self.radius), 0, int(self.radius))

logger = logging.getLogger(__name__)


class ImageMeasurementView(QWidget):
    """View for manual point-and-click tree ring measurement on images.
    
    Signals:
        series_extracted(RingWidthSeries): Emitted when user finishes 
            measuring and wants to save the series to the session.
    """
    
    series_extracted = pyqtSignal(RingWidthSeries)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dpi = 1200.0  # Default standard scanner DPI
        self._markers: list[pg.InfiniteLine] = []
        self._image_item = pg.ImageItem()
        self._has_image = False
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self._info_label = QLabel("No image loaded. DPI: 1200")
        self._info_label.setStyleSheet("color: #d4d4d4;")
        
        self._set_dpi_btn = QPushButton("Set DPI...")
        self._set_dpi_btn.clicked.connect(self._action_set_dpi)
        
        self._auto_detect_btn = QPushButton("Auto-Detect Rings (AI)")
        self._auto_detect_btn.clicked.connect(self._action_auto_detect)
        self._auto_detect_btn.setEnabled(False)
        
        self._pith_btn = QPushButton("Toggle Pith Estimator")
        self._pith_btn.setCheckable(True)
        self._pith_btn.clicked.connect(self._toggle_pith_estimator)
        
        self._clear_btn = QPushButton("Clear Markers")
        self._clear_btn.clicked.connect(self.clear_markers)
        
        self._extract_btn = QPushButton("Extract Series...")
        self._extract_btn.clicked.connect(self._action_extract_series)
        self._extract_btn.setEnabled(False)
        
        toolbar.addWidget(self._info_label)
        toolbar.addStretch()
        toolbar.addWidget(self._set_dpi_btn)
        toolbar.addWidget(self._auto_detect_btn)
        toolbar.addWidget(self._pith_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addWidget(self._extract_btn)
        layout.addLayout(toolbar)

        # Plot Widget
        self._plot = pg.PlotWidget()
        self._plot.setAspectLocked(True)
        self._plot.invertY(True)  # Images are drawn top-to-bottom
        self._plot.hideAxis('bottom')
        self._plot.hideAxis('left')
        
        self._plot.addItem(self._image_item)
        
        self._plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        
        layout.addWidget(self._plot)

    def load_image(self, filepath: str) -> None:
        """Load an image file into the viewer."""
        try:
            # We use QImage to load to handle formats, then convert to numpy
            # For extremely large TIFFs, we'd use tifffile or memory mapping, 
            # but QImage handles decent sizes well enough for MVP.
            img = QImage(filepath)
            if img.isNull():
                raise ValueError("Unsupported image format or corrupt file.")
                
            # Convert QImage to numpy array
            img = img.convertToFormat(QImage.Format.Format_RGB32)
            width = img.width()
            height = img.height()
            
            ptr = img.bits()
            ptr.setsize(height * width * 4)
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
            
            # PyQtGraph expects (x, y, color), so transpose
            # Drop alpha channel
            arr = arr[:, :, :3].transpose(1, 0, 2)
            
            self._image_item.setImage(arr)
            self._has_image = True
            self.clear_markers()
            self._plot.autoRange()
            
            self._info_label.setText(f"Loaded: {filepath.split('/')[-1]} | DPI: {self._dpi}")
            self._auto_detect_btn.setEnabled(True)
            
        except Exception as e:
            logger.exception("Failed to load image")
            QMessageBox.critical(self, "Image Error", f"Failed to load image:\n{e}")

    def clear_markers(self) -> None:
        """Remove all measurement markers."""
        for marker in self._markers:
            self._plot.removeItem(marker)
        self._markers.clear()
        self._extract_btn.setEnabled(False)

    def _on_mouse_clicked(self, evt) -> None:
        """Drop a marker on left click."""
        if not self._has_image:
            return
            
        if evt.button() == Qt.MouseButton.LeftButton:
            pos = self._image_item.mapFromScene(evt.scenePos())
            if 0 <= pos.x() <= self._image_item.width() and 0 <= pos.y() <= self._image_item.height():
                self._add_marker(pos.x())

    def _add_marker(self, x_pos: float) -> None:
        """Add a vertical line marker at pixel x_pos."""
        line = pg.InfiniteLine(
            pos=x_pos, 
            angle=90, 
            movable=True,
            pen=pg.mkPen(color="#D55E00", width=2)
        )
        line.sigPositionChangeFinished.connect(self._sort_markers)
        self._plot.addItem(line)
        self._markers.append(line)
        self._sort_markers()
        
    def _sort_markers(self) -> None:
        """Ensure markers are ordered left to right."""
        self._markers.sort(key=lambda m: m.value())
        self._extract_btn.setEnabled(len(self._markers) >= 2)
        self._update_pith_distance()

    def _toggle_pith_estimator(self, checked: bool) -> None:
        if checked:
            if not hasattr(self, '_pith_item'):
                self._pith_item = PithEstimatorItem()
                # Connect position changes to update metrics
                self._pith_item.sigPositionChangeFinished.connect(self._update_pith_distance)
            self._plot.addItem(self._pith_item)
            # Center it
            view_rect = self._plot.viewRect()
            self._pith_item.setPos(view_rect.center())
            self._update_pith_distance()
        else:
            if hasattr(self, '_pith_item'):
                self._plot.removeItem(self._pith_item)
            self._info_label.setText(f"Loaded: {self._image_item.image.shape} | DPI: {self._dpi}")
            
    def _update_pith_distance(self) -> None:
        if not hasattr(self, '_pith_item') or not self._pith_btn.isChecked():
            return
            
        if not self._markers:
            self._info_label.setText(f"DPI: {self._dpi} | Drop a marker to estimate distance")
            return
            
        # Distance from center of pith item to the first marker (innermost ring)
        pith_x = self._pith_item.pos().x()
        first_marker_x = self._markers[0].value()
        
        px_dist = abs(pith_x - first_marker_x)
        mm_dist = px_dist * (25.4 / self._dpi)
        
        self._info_label.setText(f"DPI: {self._dpi} | Est. missing distance to pith: {mm_dist:.2f} mm")

    def _action_auto_detect(self) -> None:
        """Run AI auto-detection of latewood boundaries."""
        if not self._has_image:
            return
            
        try:
            # We must get the image array directly from the item to pass to inference
            img_arr = self._image_item.image
            
            # The array is (width, height, 3). PyTorch expects (height, width, 3) 
            # or the generic proxy expects that format.
            img_arr = img_arr.transpose(1, 0, 2)
            
            from dendro.stats.ai_segmentation import extract_boundaries
            # We don't have a model.pth file so we omit it to fall back to the proxy.
            peaks_y = extract_boundaries(img_arr)
            
            if not peaks_y:
                QMessageBox.warning(self, "AI Detection", "Could not detect any clear rings in this image.")
                return
                
            self.clear_markers()
            for y in peaks_y:
                # Due to our initial transposition for PyQtGraph, x and y are swapped
                # Our proxy searches along axis=0 (height), meaning it returns indices along width
                self._add_marker(float(y))
                
            QMessageBox.information(
                self, "AI Detection", 
                f"Automatically detected {len(peaks_y)} potential boundaries.\n"
                "Please review and adjust manually before extracting."
            )
        except Exception as e:
            logger.exception("AI detection failed")
            QMessageBox.critical(self, "AI Error", f"Auto-detection failed:\n{e}")

    def _action_set_dpi(self) -> None:
        """Prompt user to set the scanner DPI."""
        dpi, ok = QInputDialog.getDouble(
            self, "Set Image DPI", 
            "Enter scanner resolution (DPI):", 
            self._dpi, 10, 10000, 1
        )
        if ok and dpi > 0:
            self._dpi = dpi
            self._info_label.setText(f"DPI: {self._dpi}")

    def _action_extract_series(self) -> None:
        """Calculate distances and extract RingWidthSeries."""
        if len(self._markers) < 2:
            return
            
        # Get x positions in pixels
        px_positions = [m.value() for m in self._markers]
        
        # Calculate pixel distances between consecutive markers
        px_widths = np.diff(px_positions)
        
        # Convert pixels to millimeters
        # 1 inch = 25.4 mm
        mm_per_px = 25.4 / self._dpi
        mm_widths = px_widths * mm_per_px
        
        series_id, ok = QInputDialog.getText(
            self, "Extract Series", 
            "Enter a unique Series ID for these measurements:",
            text="IMG_SERIES_01"
        )
        if not ok or not series_id.strip():
            return
            
        start_year, ok_year = QInputDialog.getInt(
            self, "Start Year", 
            "Enter the start year (first measured ring):",
            value=2000, min=-10000, max=2100
        )
        if not ok_year:
            return
            
        series = RingWidthSeries(
            series_id=series_id.strip(),
            widths=mm_widths,
            start_year=start_year,
            is_reference=False,
            metadata={"source": "image_measurement", "dpi": self._dpi}
        )
        
        self.series_extracted.emit(series)
        QMessageBox.information(
            self, "Success", 
            f"Extracted {len(mm_widths)} rings successfully."
        )
