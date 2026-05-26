"""dendro.ui — PyQt6 GUI components for the dendrochronology platform.

exports: MainWindow
used_by: dendro.main → application bootstrap
rules:
  - All interactive visualization uses PyQtGraph, NOT Matplotlib.
  - All data mutations must go through the CommandStack.
  - Use CVD-safe colour palette + varying line styles for accessibility.
"""
