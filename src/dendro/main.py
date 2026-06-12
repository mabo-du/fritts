"""main.py — Application entry point for the Fritts platform.

exports: main()
used_by: pyproject.toml → [project.scripts] dendro = dendro.main:main
rules:
  - Must bootstrap QApplication with high-DPI support.
  - Must set application metadata before creating any widgets.
"""

from __future__ import annotations

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    """Launch the Fritts application."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("Fritts")
    app.setApplicationDisplayName("Fritts — Dendrochronology Analysis Platform")
    app.setOrganizationName("Fritts")
    app.setApplicationVersion("0.1.3")

    # Apply dark fusion style for a modern look
    app.setStyle("Fusion")
    _apply_dark_palette(app)

    from dendro.ui.main_window import MainWindow

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _apply_dark_palette(app: "QApplication") -> None:  # noqa: F821
    """Apply a dark colour palette for a modern scientific aesthetic.

    Rules:
        - Must work across all platforms (Win/Mac/Linux).
        - Uses the Fusion style engine for consistent rendering.
    """
    from PyQt6.QtGui import QColor, QPalette

    palette = QPalette()

    # Base colours
    dark = QColor(30, 30, 30)
    mid_dark = QColor(45, 45, 48)
    mid = QColor(60, 63, 65)
    QColor(75, 78, 80)
    text_color = QColor(212, 212, 212)
    highlight = QColor(0, 114, 178)  # CVD-safe blue
    disabled_text = QColor(128, 128, 128)

    palette.setColor(QPalette.ColorRole.Window, mid_dark)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)
    palette.setColor(QPalette.ColorRole.Base, dark)
    palette.setColor(QPalette.ColorRole.AlternateBase, mid_dark)
    palette.setColor(QPalette.ColorRole.ToolTipBase, mid)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_color)
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.Button, mid_dark)
    palette.setColor(QPalette.ColorRole.ButtonText, text_color)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, highlight)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Disabled state
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text
    )

    app.setPalette(palette)

    # Fine-tune with stylesheet for specific widgets
    app.setStyleSheet(
        """
        QToolTip {
            color: #d4d4d4;
            background-color: #3c3f41;
            border: 1px solid #555;
            padding: 4px;
        }
        QMenuBar {
            background-color: #2d2d30;
            border-bottom: 1px solid #3c3f41;
        }
        QMenuBar::item:selected {
            background-color: #0072B2;
        }
        QMenu {
            background-color: #2d2d30;
            border: 1px solid #3c3f41;
        }
        QMenu::item:selected {
            background-color: #0072B2;
        }
        QStatusBar {
            background-color: #2d2d30;
            border-top: 1px solid #3c3f41;
            color: #a0a0a0;
        }
        QDockWidget::title {
            background-color: #2d2d30;
            padding: 6px;
            border: 1px solid #3c3f41;
        }
        QSplitter::handle {
            background-color: #3c3f41;
        }
        QHeaderView::section {
            background-color: #2d2d30;
            padding: 4px;
            border: 1px solid #3c3f41;
            color: #d4d4d4;
        }
        QTableWidget {
            gridline-color: #3c3f41;
        }
        QScrollBar:vertical {
            background: #2d2d30;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #555;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #0072B2;
        }
        QScrollBar:horizontal {
            background: #2d2d30;
            height: 12px;
        }
        QScrollBar::handle:horizontal {
            background: #555;
            min-width: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #0072B2;
        }
        """
    )


if __name__ == "__main__":
    main()
