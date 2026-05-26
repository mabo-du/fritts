"""itrdb_dialog.py — UI for querying and downloading from the ITRDB.

exports: ITRDBDialog
used_by: dendro.ui.main_window
rules:
  - Network IO runs on background threads (QThread) to keep UI responsive.
  - Updates table model with parsed ITRDBStudy dataclasses.
"""

from __future__ import annotations

import logging
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QLabel,
    QProgressBar,
)

from dendro.io.itrdb import search_itrdb, fetch_itrdb_series, ITRDBStudy
from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)


class SearchWorker(QThread):
    """Background thread to run ITRDB searches."""
    result_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, keyword: str):
        super().__init__()
        self.keyword = keyword

    def run(self):
        try:
            results = search_itrdb(self.keyword)
            self.result_ready.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))


class DownloadWorker(QThread):
    """Background thread to download and parse RWL files."""
    result_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            series_list = fetch_itrdb_series(self.url)
            self.result_ready.emit(series_list)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ITRDBDialog(QDialog):
    """Dialog to search and import tree-ring data from NOAA ITRDB."""

    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import from ITRDB")
        self.setMinimumSize(800, 500)
        self._session = session
        
        self._studies: list[ITRDBStudy] = []
        
        # Threads
        self._search_thread = None
        self._download_thread = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Search Bar
        search_layout = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Enter keyword (e.g., 'oak', 'colorado', 'douglas fir')")
        self._search_input.returnPressed.connect(self._on_search)
        
        self._search_btn = QPushButton("Search API")
        self._search_btn.clicked.connect(self._on_search)
        
        search_layout.addWidget(self._search_input)
        search_layout.addWidget(self._search_btn)
        layout.addLayout(search_layout)

        # Results Table
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Site Name", "Species", "Years", "Investigators", "Has RWL?"])
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemDoubleClicked.connect(self._on_download)
        
        layout.addWidget(self._table)
        
        # Status / Progress
        status_layout = QHBoxLayout()
        self._status_label = QLabel("Enter a keyword to search.")
        self._progress = QProgressBar()
        self._progress.setRange(0, 0) # Indeterminate mode
        self._progress.hide()
        
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        status_layout.addWidget(self._progress)
        layout.addLayout(status_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self._download_btn = QPushButton("Download Selected")
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.setEnabled(False)
        
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self._download_btn)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)
        
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self) -> None:
        """Enable download button if a row with an RWL url is selected."""
        row = self._table.currentRow()
        if 0 <= row < len(self._studies):
            study = self._studies[row]
            self._download_btn.setEnabled(study.rwl_url is not None)
        else:
            self._download_btn.setEnabled(False)

    def _set_busy(self, is_busy: bool, message: str) -> None:
        """Toggle UI state during background operations."""
        self._search_input.setEnabled(not is_busy)
        self._search_btn.setEnabled(not is_busy)
        self._table.setEnabled(not is_busy)
        if is_busy:
            self._download_btn.setEnabled(False)
            self._progress.show()
        else:
            self._progress.hide()
            self._on_selection_changed()
            
        self._status_label.setText(message)

    def _on_search(self) -> None:
        """Launch search thread."""
        keyword = self._search_input.text().strip()
        if not keyword:
            return
            
        self._set_busy(True, f"Searching for '{keyword}'...")
        self._table.setRowCount(0)
        self._studies.clear()
        
        self._search_thread = SearchWorker(keyword)
        self._search_thread.result_ready.connect(self._on_search_finished)
        self._search_thread.error_occurred.connect(self._on_search_error)
        self._search_thread.start()

    def _on_search_finished(self, results: list[ITRDBStudy]) -> None:
        """Populate table with search results."""
        self._studies = results
        self._table.setRowCount(len(results))
        
        for row, study in enumerate(results):
            site_item = QTableWidgetItem(study.site_name)
            # Store the study object in the first item's data for easy retrieval
            site_item.setData(Qt.ItemDataRole.UserRole, study)
            
            species_item = QTableWidgetItem(study.species)
            years_item = QTableWidgetItem(f"{study.earliest_year} - {study.most_recent_year}")
            investigators_item = QTableWidgetItem(study.investigators)
            
            has_rwl = "Yes" if study.rwl_url else "No"
            rwl_item = QTableWidgetItem(has_rwl)
            if not study.rwl_url:
                # Dim the text if no RWL is available
                rwl_item.setFlags(rwl_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                site_item.setFlags(site_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)

            self._table.setItem(row, 0, site_item)
            self._table.setItem(row, 1, species_item)
            self._table.setItem(row, 2, years_item)
            self._table.setItem(row, 3, investigators_item)
            self._table.setItem(row, 4, rwl_item)
            
        self._set_busy(False, f"Found {len(results)} studies.")

    def _on_search_error(self, err: str) -> None:
        self._set_busy(False, "Search failed.")
        QMessageBox.critical(self, "Search Error", f"ITRDB Search failed:\n{err}")

    def _on_download(self) -> None:
        """Launch download thread for selected study."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._studies):
            return
            
        study = self._studies[row]
        if not study.rwl_url:
            QMessageBox.information(self, "No RWL", "This study does not have a raw ring-width file available for download.")
            return
            
        self._set_busy(True, f"Downloading {study.site_name}...")
        
        self._download_thread = DownloadWorker(study.rwl_url)
        self._download_thread.result_ready.connect(self._on_download_finished)
        self._download_thread.error_occurred.connect(self._on_download_error)
        self._download_thread.start()

    def _on_download_finished(self, series_list: list[RingWidthSeries]) -> None:
        self._set_busy(False, "Download complete.")
        
        imported_count = 0
        for series in series_list:
            original_id = series.series_id
            suffix = 1
            while self._session.has_series(series.series_id):
                series.series_id = f"{original_id}_{suffix}"
                suffix += 1
            self._session.add_series(series)
            imported_count += 1
            
        QMessageBox.information(self, "Import Successful", f"Imported {imported_count} series from ITRDB.")
        
    def _on_download_error(self, err: str) -> None:
        self._set_busy(False, "Download failed.")
        QMessageBox.critical(self, "Download Error", f"Failed to download or parse series:\n{err}")
