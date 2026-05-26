"""qc_dialog.py — Dialog to display the COFECHA Quality Control Report.

exports: QCDialog
used_by:
  dendro.ui.main_window -> Analysis menu
rules:
  - Display report text in a read-only monospace text browser.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTextBrowser,
    QDialogButtonBox,
)
from PyQt6.QtGui import QFont

class QCDialog(QDialog):
    """Dialog to display the results of a Quality Control run."""

    def __init__(self, report_text: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quality Control Report")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        self._text_browser = QTextBrowser()
        self._text_browser.setFont(QFont("Monospace", 10))
        self._text_browser.setPlainText(report_text)
        layout.addWidget(self._text_browser)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)
