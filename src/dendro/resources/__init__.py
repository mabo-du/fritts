"""dendro.resources — Icons, colour palettes, and static assets.

exports: CVD_SAFE_PALETTE, LINE_STYLES
used_by: dendro.ui.series_view → series rendering
rules:
  - Palette must be distinguishable under protanopia, deuteranopia, tritanopia.
"""

# Wong (2011) CVD-safe colour palette — 8 colours distinguishable
# under all common forms of colour vision deficiency.
CVD_SAFE_PALETTE = [
    "#0072B2",  # Blue
    "#D55E00",  # Vermillion
    "#009E73",  # Bluish green
    "#CC79A7",  # Reddish purple
    "#E69F00",  # Orange
    "#56B4E9",  # Sky blue
    "#F0E442",  # Yellow
    "#000000",  # Black
]

# Line styles to combine with colours for additional differentiation.
from PyQt6.QtCore import Qt

LINE_STYLES = [
    Qt.PenStyle.SolidLine,
    Qt.PenStyle.DashLine,
    Qt.PenStyle.DotLine,
    Qt.PenStyle.DashDotLine,
    Qt.PenStyle.DashDotDotLine,
]
