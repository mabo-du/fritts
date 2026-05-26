"""detrend_dialog.py — Dialog for configuring and applying detrending to series.

exports: DetrendDialog
used_by:
  dendro.ui.main_window -> Analysis menu
rules:
  - Validates selections before execution
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDialogButtonBox,
    QSpinBox,
    QMessageBox,
)

class DetrendDialog(QDialog):
    """Dialog to configure detrending parameters."""

    def __init__(self, session, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detrend Series")
        self._session = session
        self.setMinimumWidth(300)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Target Selection
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target:"))
        self._target_combo = QComboBox()
        self._target_combo.addItem("All Series", "_all_")
        for sid in self._session.series_ids:
            self._target_combo.addItem(sid, sid)
        target_layout.addWidget(self._target_combo)
        layout.addLayout(target_layout)

        # Method Selection
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Method:"))
        self._method_combo = QComboBox()
        self._method_combo.addItem("Spline (Cubic Smoothing)", "spline")
        self._method_combo.addItem("Negative Exponential", "neg_exp")
        self._method_combo.addItem("Hugershoff Polynomial", "hugershoff")
        self._method_combo.addItem("Regional Curve Standardisation (RCS)", "rcs")
        self._method_combo.addItem("Mean", "mean")
        method_layout.addWidget(self._method_combo)
        layout.addLayout(method_layout)
        
        # Method constraints: RCS requires "All Series"
        self._method_combo.currentTextChanged.connect(self._on_method_changed)
        
        # Spline Stiffness (only relevant for spline)
        self._stiffness_layout = QHBoxLayout()
        self._stiffness_layout.addWidget(QLabel("Spline Stiffness:"))
        self._stiffness_spin = QSpinBox()
        self._stiffness_spin.setRange(1, 1000)
        self._stiffness_spin.setValue(10)
        self._stiffness_spin.setToolTip("Higher values = flatter curve (less responsive to fast changes)")
        self._stiffness_layout.addWidget(self._stiffness_spin)
        layout.addLayout(self._stiffness_layout)
        
        # Toggle stiffness visibility based on method
        self._method_combo.currentTextChanged.connect(
            lambda: self._stiffness_spin.setEnabled(self._method_combo.currentData() == "spline")
        )

        # Buttons
        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)
        layout.addWidget(self._button_box)

    def _on_method_changed(self) -> None:
        method = self._method_combo.currentData()
        self._stiffness_spin.setEnabled(method == "spline")
        if method == "rcs":
            # RCS is population-based, force All Series
            idx = self._target_combo.findData("_all_")
            if idx >= 0:
                self._target_combo.setCurrentIndex(idx)
            self._target_combo.setEnabled(False)
        else:
            self._target_combo.setEnabled(True)

    @property
    def target_series_id(self) -> str:
        return self._target_combo.currentData()

    @property
    def method(self) -> str:
        return self._method_combo.currentData()
        
    @property
    def stiffness(self) -> int:
        return self._stiffness_spin.value()
