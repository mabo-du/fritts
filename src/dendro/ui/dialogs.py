"""dialogs.py — Modal dialogs for import, export, cross-dating, and about.

exports: ImportDialog, ExportDialog, CrossDateDialog, AboutDialog
used_by:
  dendro.ui.main_window → menu/toolbar actions
rules:
  - ImportDialog auto-detects format from file extension.
  - ImportDialog shows BC/BCE convention selector when negative years detected.
  - CrossDateDialog lets user choose sample vs. reference and min overlap.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from dendro.models.session import SessionManager

logger = logging.getLogger(__name__)

# Supported file format filters
_IMPORT_FILTERS = (
    "All Supported Formats (*.rwl *.tuc *.crn *.fh *.xml);;"
    "Tucson Decadal (*.rwl *.tuc *.crn);;"
    "Heidelberg (*.fh);;"
    "TRiDaS XML (*.xml);;"
    "All Files (*)"
)

_EXPORT_FILTERS = "Tucson Decadal (*.rwl);;TRiDaS XML (*.xml);;All Files (*)"


class ImportDialog(QDialog):
    """File import dialog with format auto-detection and options.

    Attributes:
        filepath: Selected file path (or None if cancelled).
        format_hint: Detected format string ('tucson', 'heidelberg', 'tridas').

    Rules:
        - Auto-detects format from extension.
        - Shows BC/BCE convention selector if file contains negative years.
    """

    def __init__(self, parent=None, last_dir: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Import Ring-Width Data")
        self.setMinimumWidth(500)

        self.filepath: Path | None = None
        self.format_hint: str = "auto"

        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout(file_group)

        self._file_label = QLabel("No file selected")
        self._file_label.setStyleSheet("color: #a0a0a0; padding: 4px;")
        file_layout.addRow("File:", self._file_label)

        browse_btn = QDialogButtonBox()
        browse_btn.addButton("Browse…", QDialogButtonBox.ButtonRole.ActionRole)
        browse_btn.clicked.connect(lambda: self._browse(last_dir))
        file_layout.addRow(browse_btn)
        layout.addWidget(file_group)

        # Options
        options_group = QGroupBox("Import Options")
        options_layout = QFormLayout(options_group)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["Auto-detect", "Tucson (.rwl)", "Heidelberg (.fh)", "TRiDaS (.xml)"])
        options_layout.addRow("Format:", self._format_combo)

        self._bce_combo = QComboBox()
        self._bce_combo.addItems([
            "Astronomical (year 0 exists: …, -1, 0, 1, …)",
            "Historical (no year 0: …, 2 BC, 1 BC, 1 AD, …)",
        ])
        self._bce_combo.setToolTip(
            "Tucson format does not mandate a year-zero convention.\n"
            "If your data contains BCE dates, select the correct convention\n"
            "to avoid off-by-one century errors."
        )
        options_layout.addRow("BCE Convention:", self._bce_combo)
        layout.addWidget(options_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self, last_dir: str) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Ring-Width Data File", last_dir, _IMPORT_FILTERS
        )
        if filepath:
            self.filepath = Path(filepath)
            self._file_label.setText(str(self.filepath))
            self._file_label.setStyleSheet("color: #d4d4d4; padding: 4px;")
            # Auto-detect format
            ext = self.filepath.suffix.lower()
            if ext in (".rwl", ".tuc", ".crn"):
                self._format_combo.setCurrentIndex(1)
            elif ext == ".fh":
                self._format_combo.setCurrentIndex(2)
            elif ext == ".xml":
                self._format_combo.setCurrentIndex(3)

    def _on_accept(self) -> None:
        if self.filepath is None:
            return
        fmt_idx = self._format_combo.currentIndex()
        self.format_hint = ["auto", "tucson", "heidelberg", "tridas"][fmt_idx]
        self.accept()

    @property
    def bce_astronomical(self) -> bool:
        """True if user selected astronomical year numbering."""
        return self._bce_combo.currentIndex() == 0


class ExportDialog(QDialog):
    """File export dialog for saving series to .rwl format.

    Rules:
        - Precision selector for 0.01mm vs. 0.001mm output.
    """

    def __init__(self, parent=None, last_dir: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Export Ring-Width Data")
        self.setMinimumWidth(450)

        self.filepath: Path | None = None

        layout = QVBoxLayout(self)

        options_group = QGroupBox("Export Options")
        options_layout = QFormLayout(options_group)

        self._precision_combo = QComboBox()
        self._precision_combo.addItems(["0.01 mm (stop code 999)", "0.001 mm (stop code -9999)"])
        options_layout.addRow("Precision:", self._precision_combo)
        layout.addWidget(options_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(lambda: self._on_save(last_dir))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_save(self, last_dir: str) -> None:
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Ring-Width File", last_dir, _EXPORT_FILTERS
        )
        if filepath:
            self.filepath = Path(filepath)
            self.accept()

    @property
    def precision(self) -> str:
        return "0.001mm" if self._precision_combo.currentIndex() == 1 else "0.01mm"


class CrossDateDialog(QDialog):
    """Dialog for configuring a cross-dating analysis run.

    Attributes:
        sample_id: Selected floating sample series ID.
        reference_id: Selected reference series ID.
        min_overlap: Minimum overlap in years.

    Rules:
        - sample_id and reference_id must differ.
        - min_overlap must be >= 30 (50 recommended).
    """

    def __init__(self, session: "SessionManager", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cross-Date Series")
        self.setMinimumWidth(400)

        self.sample_id: str = ""
        self.reference_id: str = ""
        self.min_overlap: int = 50

        layout = QVBoxLayout(self)

        form_group = QGroupBox("Cross-Dating Configuration")
        form = QFormLayout(form_group)

        self._sample_combo = QComboBox()
        self._reference_combo = QComboBox()

        for sid in session.series_ids:
            series = session.get_series(sid)
            label = f"{sid} ({series.start_year}–{series.end_year}, n={series.ring_count})"
            self._sample_combo.addItem(label, sid)
            self._reference_combo.addItem(label, sid)

        # Pre-select: first floating as sample, first reference as reference
        for i, sid in enumerate(session.series_ids):
            s = session.get_series(sid)
            if not s.is_reference:
                self._sample_combo.setCurrentIndex(i)
                break
        for i, sid in enumerate(session.series_ids):
            s = session.get_series(sid)
            if s.is_reference:
                self._reference_combo.setCurrentIndex(i)
                break

        form.addRow("Sample (floating):", self._sample_combo)
        form.addRow("Reference (dated):", self._reference_combo)

        self._overlap_spin = QSpinBox()
        self._overlap_spin.setRange(30, 500)
        self._overlap_spin.setValue(50)
        self._overlap_spin.setToolTip("Minimum number of overlapping years for valid statistics.")
        form.addRow("Min. overlap (years):", self._overlap_spin)

        layout.addWidget(form_group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        self.sample_id = self._sample_combo.currentData()
        self.reference_id = self._reference_combo.currentData()
        self.min_overlap = self._overlap_spin.value()
        if self.sample_id == self.reference_id:
            logger.warning("Sample and reference must be different series.")
            return
        self.accept()


class AboutDialog(QDialog):
    """About dialog showing version, license, and credits."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("About Fritts")
        self.setFixedSize(500, 380)

        layout = QVBoxLayout(self)

        title = QLabel("Fritts")
        title.setFont(QFont("Inter", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #0072B2;")
        layout.addWidget(title)

        subtitle = QLabel("Dendrochronology Analysis Platform")
        subtitle.setFont(QFont("Inter", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(subtitle)

        version = QLabel("Version 0.1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: #888; padding: 8px;")
        layout.addWidget(version)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setHtml(
            "<p style='color:#d4d4d4; text-align:center;'>"
            "An open-source desktop tool for tree-ring cross-dating,<br>"
            "measurement, and master chronology building.</p>"
            "<p style='color:#0072B2; text-align:center; font-style:italic;'>"
            "Named in honor of Dr. Harold C. \"Hal\" Fritts (1928–2019),<br>"
            "a pioneer of dendroclimatology who laid the computational<br>"
            "foundation for modern tree-ring science.</p>"
            "<p style='color:#888; text-align:center;'>License: MIT</p>"
            "<p style='color:#888; text-align:center;'>"
            "Built with PyQt6, PyQtGraph, NumPy, SciPy, and Pandas.</p>"
        )
        info.setStyleSheet(
            "QTextBrowser { background-color: transparent; border: none; }"
        )
        layout.addWidget(info)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
