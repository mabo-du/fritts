"""main_window.py — Main application window orchestrating all UI components.

exports: MainWindow
used_by:
  dendro.main → main() creates and shows MainWindow
rules:
  - Owns the SessionManager and CommandStack — single source of truth.
  - All data mutations go through CommandStack.
  - Menu/toolbar actions delegate to private _action_* methods.
  - Status bar shows cursor position and series info.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QStatusBar,
    QToolBar,
    QMessageBox,
    QLabel,
    QTabWidget,
    QFileDialog,
)

from dendro.models.session import SessionManager
from dendro.models.commands import (
    CommandStack,
    InsertRingCommand,
    DeleteRingCommand,
    ShiftSeriesCommand,
    DetrendCommand,
)
from dendro.ui.series_view import SeriesView
from dendro.ui.stats_panel import StatsPanel
from dendro.ui.series_list import SeriesListPanel
from dendro.ui.dialogs import (
    ImportDialog,
    ExportDialog,
    CrossDateDialog,
    AboutDialog,
)
from dendro.ui.detrend_dialog import DetrendDialog
from dendro.ui.itrdb_dialog import ITRDBDialog
from dendro.ui.image_view import ImageMeasurementView

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for the Fritts platform.

    Layout:
        ┌──────────┬────────────────────────────────┐
        │ Series   │   SeriesView (PyQtGraph)       │
        │ List     │   ─ ring-width curves ─        │
        │ (dock)   ├────────────────────────────────┤
        │          │   StatsPanel                   │
        │          │   ─ score plot + results table ─│
        └──────────┴────────────────────────────────┘
        [ Status Bar: Year | Series Count | Overlap ]

    Rules:
        - Single SessionManager instance shared across all components.
        - CommandStack handles all undo/redo.
        - Keyboard shortcuts: Ctrl+O (import), Ctrl+S (export),
          Ctrl+Z (undo), Ctrl+Shift+Z (redo), ←/→ (shift series).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fritts — Dendrochronology Analysis Platform")
        self.setMinimumSize(1200, 700)
        self.resize(1440, 900)

        # Core state
        self._session = SessionManager()
        self._command_stack = CommandStack(self._session)
        self._last_import_dir = str(Path.home())
        self._active_sample_id: str | None = None

        # UI components
        self._series_view = SeriesView(self._session)
        self._image_view = ImageMeasurementView()
        self._stats_panel = StatsPanel()
        self._series_list = SeriesListPanel(self._session)

        from dendro.ui.chronology_builder import ChronologyBuilderDock
        self._chronology_dock = ChronologyBuilderDock(self._session, self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._chronology_dock)
        self._chronology_dock.hide()

        self._setup_layout()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #

    def _setup_layout(self) -> None:
        """Build the main window layout."""
        # Top half is tabs (Series / Image)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._series_view, "Series Canvas")
        self._tabs.addTab(self._image_view, "Image Measurement")
        
        # Central splitter: tabs (top) + stats panel (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._tabs)
        splitter.addWidget(self._stats_panel)
        splitter.setSizes([550, 250])
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        # Left dock: series list
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._series_list)

    # ------------------------------------------------------------------ #
    # Menus
    # ------------------------------------------------------------------ #

    def _setup_menus(self) -> None:
        """Build the menu bar."""
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        self._import_action = QAction("&Import Series…", self)
        self._import_action.setShortcut(QKeySequence.StandardKey.Open)
        self._import_action.triggered.connect(self._action_import)
        file_menu.addAction(self._import_action)
        
        self._import_image_action = QAction("Import &Image Scan…", self)
        self._import_image_action.triggered.connect(self._action_import_image)
        file_menu.addAction(self._import_image_action)
        
        self._import_itrdb_action = QAction("Import from &ITRDB…", self)
        self._import_itrdb_action.triggered.connect(self._action_import_itrdb)
        file_menu.addAction(self._import_itrdb_action)

        self._export_action = QAction("&Export…", self)
        self._export_action.setShortcut(QKeySequence.StandardKey.Save)
        self._export_action.triggered.connect(self._action_export)
        file_menu.addAction(self._export_action)
        
        self._export_r_action = QAction("Generate &R Script (dplR)…", self)
        self._export_r_action.triggered.connect(self._action_export_r_script)
        file_menu.addAction(self._export_r_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")

        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._command_stack.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._command_stack.redo)
        edit_menu.addAction(self._redo_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        self._normalize_action = QAction("&Normalize (Z-score)", self)
        self._normalize_action.setCheckable(True)
        self._normalize_action.setChecked(False)
        self._normalize_action.triggered.connect(
            lambda checked: self._series_view.set_normalize(checked)
        )
        view_menu.addAction(self._normalize_action)
        
        self._show_indices_action = QAction("Show &Detrended Indices (RWI)", self)
        self._show_indices_action.setCheckable(True)
        self._show_indices_action.setChecked(False)
        self._show_indices_action.triggered.connect(
            lambda checked: self._series_view.set_show_indices(checked)
        )
        view_menu.addAction(self._show_indices_action)

        self._show_skeleton_action = QAction("Show S&keleton Plot", self)
        self._show_skeleton_action.setCheckable(True)
        self._show_skeleton_action.setChecked(False)
        self._show_skeleton_action.triggered.connect(
            lambda checked: self._series_view.set_show_skeleton(checked)
        )
        view_menu.addAction(self._show_skeleton_action)

        zoom_fit_action = QAction("Zoom to &Fit", self)
        zoom_fit_action.setShortcut("F")
        zoom_fit_action.triggered.connect(
            lambda: self._series_view.autoRange()
        )
        view_menu.addAction(zoom_fit_action)

        # Analysis menu
        analysis_menu = menu_bar.addMenu("&Analysis")

        self._crossdate_action = QAction("&Cross-Date…", self)
        self._crossdate_action.setShortcut("Ctrl+D")
        self._crossdate_action.triggered.connect(self._action_crossdate)
        analysis_menu.addAction(self._crossdate_action)
        
        self._detrend_action = QAction("De&trend Series…", self)
        self._detrend_action.triggered.connect(self._action_detrend)
        analysis_menu.addAction(self._detrend_action)
        
        self._qc_action = QAction("Quality Control (&COFECHA)…", self)
        self._qc_action.triggered.connect(self._action_qc)
        analysis_menu.addAction(self._qc_action)
        
        self._interactive_chronology_action = QAction("Interactive Chronology Builder", self)
        self._interactive_chronology_action.setCheckable(True)
        self._interactive_chronology_action.triggered.connect(
            lambda checked: self._chronology_dock.setVisible(checked)
        )
        self._chronology_dock.visibilityChanged.connect(
            self._interactive_chronology_action.setChecked
        )
        analysis_menu.addAction(self._interactive_chronology_action)

        self._chronology_action = QAction("Build Master &Chronology (Auto)", self)
        self._chronology_action.setShortcut("Ctrl+B")
        self._chronology_action.triggered.connect(self._action_build_chronology)
        analysis_menu.addAction(self._chronology_action)

        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About Fritts", self)
        about_action.triggered.connect(lambda: AboutDialog(self).exec())
        help_menu.addAction(about_action)

    # ------------------------------------------------------------------ #
    # Toolbar
    # ------------------------------------------------------------------ #

    def _setup_toolbar(self) -> None:
        """Build the main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            """
            QToolBar {
                background-color: #2d2d30;
                border-bottom: 1px solid #3c3f41;
                spacing: 4px;
                padding: 2px;
            }
            QToolButton {
                color: #d4d4d4;
                padding: 6px 12px;
                border: 1px solid transparent;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #3c3f41;
                border-color: #555;
            }
            QToolButton:pressed {
                background-color: #0072B2;
            }
            """
        )
        toolbar.addAction(self._import_action)
        toolbar.addAction(self._export_action)
        toolbar.addSeparator()
        toolbar.addAction(self._undo_action)
        toolbar.addAction(self._redo_action)
        toolbar.addSeparator()
        toolbar.addAction(self._crossdate_action)
        toolbar.addAction(self._detrend_action)
        toolbar.addAction(self._chronology_action)
        self.addToolBar(toolbar)

    # ------------------------------------------------------------------ #
    # Status bar
    # ------------------------------------------------------------------ #

    def _setup_statusbar(self) -> None:
        """Build the status bar."""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

        self._status_year = QLabel("Year: —")
        self._status_year.setFont(QFont("Inter", 9))
        self._statusbar.addWidget(self._status_year)

        self._status_count = QLabel("Series: 0")
        self._status_count.setFont(QFont("Inter", 9))
        self._statusbar.addPermanentWidget(self._status_count)

    # ------------------------------------------------------------------ #
    # Signal connections
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        """Wire up all cross-component signals."""
        # Command stack state → undo/redo button enable
        self._command_stack.state_changed.connect(self._update_undo_redo_state)

        # Series list visibility toggle → series view
        self._series_list.visibility_changed.connect(
            self._series_view.set_series_visible
        )

        # Series list context menu actions
        self._series_list.series_remove_requested.connect(self._action_remove_series)
        self._series_list.set_reference_requested.connect(self._action_set_reference)
        self._series_list.series_selected.connect(self._auto_crossdate)
        
        # Image view signals
        self._image_view.series_extracted.connect(self._on_image_series_extracted)

        # Series view signals → command stack
        self._series_view.phantom_ring_requested.connect(
            lambda sid, year: self._command_stack.execute(
                InsertRingCommand(sid, year, 0.0)
            )
        )
        self._series_view.delete_ring_requested.connect(
            lambda sid, year: self._command_stack.execute(
                DeleteRingCommand(sid, year)
            )
        )

        # Cursor position → status bar
        self._series_view.year_hovered.connect(
            lambda year: self._status_year.setText(f"Year: {year}")
        )

        # Stats panel offset selection → shift floating series
        self._stats_panel.offset_selected.connect(self._action_snap_to_offset)

        # Session changes → update status bar
        self._session.series_added.connect(lambda _: self._update_status_count())
        self._session.series_removed.connect(lambda _: self._update_status_count())
        self._session.session_cleared.connect(self._update_status_count)

        # Arrow keys → shift active sample
        # (Handled via keyPressEvent override)

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #

    def _action_import(self) -> None:
        """Open the import dialog and load series from file."""
        dialog = ImportDialog(self, last_dir=self._last_import_dir)
        if dialog.exec() != ImportDialog.DialogCode.Accepted:
            return
        if dialog.filepath is None:
            return

        self._last_import_dir = str(dialog.filepath.parent)
        filepath = dialog.filepath
        fmt = dialog.format_hint

        # Auto-detect format from extension if needed
        if fmt == "auto":
            ext = filepath.suffix.lower()
            if ext in (".rwl", ".tuc", ".crn"):
                fmt = "tucson"
            elif ext == ".fh":
                fmt = "heidelberg"
            elif ext == ".xml":
                fmt = "tridas"
            else:
                QMessageBox.warning(
                    self, "Unknown Format",
                    f"Cannot determine format for extension '{ext}'.\n"
                    "Please select the format manually.",
                )
                return

        try:
            if fmt == "tucson":
                from dendro.io.tucson import read_tucson
                series_list = read_tucson(str(filepath))
            elif fmt == "heidelberg":
                from dendro.io.heidelberg import read_heidelberg
                series_list = read_heidelberg(str(filepath))
            elif fmt == "tridas":
                from dendro.io.tridas import read_tridas
                series_list = read_tridas(str(filepath))
            else:
                QMessageBox.warning(self, "Error", f"Unsupported format: {fmt}")
                return

            for series in series_list:
                # Handle duplicate IDs by appending a suffix
                original_id = series.series_id
                suffix = 1
                while self._session.has_series(series.series_id):
                    series.series_id = f"{original_id}_{suffix}"
                    suffix += 1
                self._session.add_series(series)

            logger.info(
                "Imported %d series from %s", len(series_list), filepath.name
            )
            self._series_view.autoRange()

        except Exception as e:
            logger.exception("Import failed")
            QMessageBox.critical(
                self, "Import Error",
                f"Failed to import {filepath.name}:\n\n{e}",
            )
            
    def _action_import_image(self) -> None:
        """Open a high-res scan for image measurement."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Image Scan", self._last_import_dir,
            "Images (*.png *.jpg *.jpeg *.tif *.tiff);;All Files (*)"
        )
        if filepath:
            from pathlib import Path
            self._last_import_dir = str(Path(filepath).parent)
            self._image_view.load_image(filepath)
            self._tabs.setCurrentWidget(self._image_view)
            
    def _on_image_series_extracted(self, series) -> None:
        """Handle series extracted from the image view."""
        # Handle duplicates
        original_id = series.series_id
        suffix = 1
        while self._session.has_series(series.series_id):
            series.series_id = f"{original_id}_{suffix}"
            suffix += 1
            
        self._session.add_series(series)
        self._tabs.setCurrentWidget(self._series_view)
        self._series_view.autoRange()

    def _action_import_itrdb(self) -> None:
        """Open the ITRDB search and import dialog."""
        dialog = ITRDBDialog(self._session, self)
        dialog.exec()

    def _action_export(self) -> None:
        """Open the export dialog and save series to file."""
        if self._session.series_count == 0:
            QMessageBox.information(self, "Nothing to Export", "No series loaded.")
            return

        dialog = ExportDialog(self, last_dir=self._last_import_dir)
        if dialog.exec() != ExportDialog.DialogCode.Accepted:
            return
        if dialog.filepath is None:
            return

        try:
            if dialog.filepath.suffix.lower() == ".xml":
                from dendro.io.tridas import write_tridas
                write_tridas(
                    self._session.all_series,
                    str(dialog.filepath),
                )
            else:
                from dendro.io.tucson import write_tucson
                write_tucson(
                    self._session.all_series,
                    str(dialog.filepath),
                    precision=dialog.precision,
                )
            
            logger.info("Exported %d series to %s",
                        self._session.series_count, dialog.filepath.name)
            self._statusbar.showMessage(f"Exported to {dialog.filepath.name}", 5000)

        except Exception as e:
            logger.exception("Export failed")
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export:\n\n{e}",
            )

    def _action_export_r_script(self) -> None:
        """Export workspace to Tucson and generate a companion R script."""
        if self._session.series_count == 0:
            QMessageBox.information(self, "Nothing to Export", "No series loaded.")
            return

        from dendro.io.export_r import generate_dplr_script
        from dendro.io.tucson import write_tucson

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Generate R Script", self._last_import_dir, "R Script (*.R);;All Files (*)"
        )
        if not filepath:
            return

        r_path = Path(filepath)
        if r_path.suffix.lower() != ".r":
            r_path = r_path.with_suffix(".R")
            
        tucson_path = r_path.with_suffix(".rwl")

        try:
            write_tucson(self._session.all_series, str(tucson_path))
            generate_dplr_script(str(r_path), str(tucson_path))

            logger.info("Generated R script %s and data %s", r_path.name, tucson_path.name)
            self._statusbar.showMessage(f"Generated {r_path.name}", 5000)

        except Exception as e:
            logger.exception("Failed to generate R script")
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to generate R script:\n\n{e}",
            )

    def _action_crossdate(self) -> None:
        """Open the cross-dating dialog and run analysis."""
        if self._session.series_count < 2:
            QMessageBox.information(
                self, "Insufficient Data",
                "At least two series are required for cross-dating.",
            )
            return

        dialog = CrossDateDialog(self._session, self)
        if dialog.exec() != CrossDateDialog.DialogCode.Accepted:
            return

        try:
            from dendro.stats.crossdate import crossdate_sliding
            sample = self._session.get_series(dialog.sample_id)
            reference = self._session.get_series(dialog.reference_id)

            results = crossdate_sliding(
                sample, reference, min_overlap=dialog.min_overlap
            )
            self._stats_panel.display_results(results)
            self._active_sample_id = dialog.sample_id

            logger.info(
                "Cross-dating: %s vs %s — %d positions tested",
                dialog.sample_id, dialog.reference_id, len(results),
            )

        except Exception as e:
            logger.exception("Cross-dating failed")
            QMessageBox.critical(
                self, "Cross-Dating Error",
                f"Analysis failed:\n\n{e}",
            )

    def _action_qc(self) -> None:
        """Run COFECHA-style quality control report."""
        if self._session.series_count < 2:
            QMessageBox.information(self, "Insufficient Data", "At least two series are required for Quality Control.")
            return
            
        from dendro.stats.quality_control import run_cofecha_check
        from dendro.ui.qc_dialog import QCDialog
        
        report = run_cofecha_check(self._session.all_series)
        dialog = QCDialog(report, self)
        dialog.exec()

    def _action_detrend(self) -> None:
        """Open the detrending dialog and apply to series."""
        if self._session.series_count == 0:
            QMessageBox.information(self, "No Series", "No series loaded to detrend.")
            return

        dialog = DetrendDialog(self._session, self)
        if dialog.exec() != DetrendDialog.DialogCode.Accepted:
            return

        try:
            from dendro.stats.detrend import detrend_series, rcs_detrend
            target = dialog.target_series_id
            method = dialog.method
            stiffness = dialog.stiffness
            
            targets = self._session.series_ids if target == "_all_" else [target]
            
            if method == "rcs":
                series_list = [self._session.get_series(sid) for sid in targets]
                rcs_results = rcs_detrend(series_list)
                for sid, rwi in rcs_results.items():
                    self._command_stack.execute(
                        DetrendCommand(sid, rwi, method)
                    )
            else:
                for sid in targets:
                    series = self._session.get_series(sid)
                    rwi = detrend_series(series.widths, method=method, stiffness=stiffness)
                    self._command_stack.execute(
                        DetrendCommand(sid, rwi, method)
                    )
            logger.info(f"Detrended {len(targets)} series using {method}.")
            self._statusbar.showMessage(f"Detrended {len(targets)} series.", 5000)

            # Auto-switch to showing indices if we just detrended
            self._show_indices_action.setChecked(True)
            self._series_view.set_show_indices(True)

        except Exception as e:
            logger.exception("Detrending failed")
            QMessageBox.critical(
                self, "Detrending Error",
                f"Detrending failed:\n\n{e}",
            )

    def _action_build_chronology(self) -> None:
        """Build a master chronology from all reference series."""
        ref_series = self._session.reference_series
        if len(ref_series) < 2:
            QMessageBox.information(
                self, "Insufficient References",
                "At least two reference series are required to build a chronology.\n"
                "Right-click series in the list to mark them as references.",
            )
            return

        try:
            from dendro.stats.chronology import build_chronology
            chronology, sample_depth = build_chronology(ref_series)

            # Add to session (remove existing chronology if present)
            if self._session.has_series("CHRONOLOGY"):
                self._session.remove_series("CHRONOLOGY")
            self._session.add_series(chronology)

            logger.info(
                "Built chronology: %d–%d (%d years), max depth %d",
                chronology.start_year, chronology.end_year,
                chronology.ring_count, int(sample_depth.max()),
            )
            self._statusbar.showMessage(
                f"Chronology built: {chronology.start_year}–{chronology.end_year}", 5000
            )

        except Exception as e:
            logger.exception("Chronology building failed")
            QMessageBox.critical(
                self, "Chronology Error",
                f"Failed to build chronology:\n\n{e}",
            )

    def _action_remove_series(self, series_id: str) -> None:
        """Remove a series from the session."""
        self._session.remove_series(series_id)
        if self._active_sample_id == series_id:
            self._active_sample_id = None
            self._stats_panel.clear_results()

    def _action_set_reference(self, series_id: str) -> None:
        """Toggle a series as reference/floating."""
        series = self._session.get_series(series_id)
        series.is_reference = not series.is_reference
        self._session.replace_series(series_id, series)
        
    def _auto_crossdate(self, series_id: str) -> None:
        """Automatically crossdate a floating series against the best available reference."""
        try:
            series = self._session.get_series(series_id)
        except KeyError:
            return
            
        if series.is_reference:
            # Don't auto-crossdate references
            return
            
        references = self._session.reference_series
        if not references:
            self._statusbar.showMessage("No reference series available for auto-crossdating.", 3000)
            return
            
        # Prefer the master CHRONOLOGY if it exists, otherwise pick the first reference
        reference = None
        if self._session.has_series("CHRONOLOGY"):
            reference = self._session.get_series("CHRONOLOGY")
        else:
            reference = references[0]
            
        try:
            from dendro.stats.crossdate import crossdate_sliding
            self._active_sample_id = series_id
            
            # Use detrended indices if available, otherwise raw widths
            # The crossdate algorithms (t_BP) apply their own internal standardisation, 
            # so raw widths is also perfectly fine. crossdate_sliding handles RingWidthSeries directly.
            results = crossdate_sliding(series, reference, min_overlap=30)
            self._stats_panel.display_results(results)
            
            logger.info("Auto-crossdated %s vs %s", series_id, reference.series_id)
            self._statusbar.showMessage(f"Auto-crossdated {series_id} vs {reference.series_id}", 3000)
        except Exception:
            logger.exception("Auto-crossdating failed")

    def _action_snap_to_offset(self, proposed_start_year: int) -> None:
        """Shift the active sample series to a proposed start year."""
        if self._active_sample_id is None:
            return
        series = self._session.get_series(self._active_sample_id)
        offset = proposed_start_year - series.start_year
        if offset != 0:
            self._command_stack.execute(
                ShiftSeriesCommand(self._active_sample_id, offset)
            )

    # ------------------------------------------------------------------ #
    # Keyboard handling
    # ------------------------------------------------------------------ #

    def keyPressEvent(self, event) -> None:
        """Handle arrow keys for shifting the active floating sample."""
        if self._active_sample_id is None:
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key.Key_Left:
            self._command_stack.execute(
                ShiftSeriesCommand(self._active_sample_id, -1)
            )
        elif event.key() == Qt.Key.Key_Right:
            self._command_stack.execute(
                ShiftSeriesCommand(self._active_sample_id, 1)
            )
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------ #
    # UI state updates
    # ------------------------------------------------------------------ #

    def _update_undo_redo_state(self) -> None:
        """Update undo/redo action enabled state and text."""
        self._undo_action.setEnabled(self._command_stack.can_undo)
        self._redo_action.setEnabled(self._command_stack.can_redo)
        if self._command_stack.can_undo:
            self._undo_action.setText(f"Undo: {self._command_stack.undo_description}")
        else:
            self._undo_action.setText("Undo")
        if self._command_stack.can_redo:
            self._redo_action.setText(f"Redo: {self._command_stack.redo_description}")
        else:
            self._redo_action.setText("Redo")

    def _update_status_count(self) -> None:
        """Update series count in status bar."""
        n = self._session.series_count
        self._status_count.setText(f"Series: {n}")
