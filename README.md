# Fritts — Dendrochronology Analysis Platform

![Fritts Screenshot](assets/fritts.png)

An open-source desktop tool for tree-ring cross-dating, measurement, and master chronology building. Built with Python, PyQt6, and PyQtGraph. Named in honor of Harold C. Fritts, a pioneer of dendroclimatology.

## Why Fritts?

Existing dendrochronology software is often dated, proprietary, Windows-only, or splits critical workflows across multiple applications. **Fritts** unifies format parsing, interactive visual plotting, statistical cross-dating, and chronology building into a single, modern, cross-platform interface.

## Features (v3.0 Masterpiece)

- **Multi-format import** — Tucson (.rwl/.tuc), Heidelberg (.fh), TRiDaS XML
- **Interactive plotting** — PyQtGraph-powered canvas with smooth zoom, pan, and multi-series overlay
- **Statistical cross-dating** — Baillie-Pilcher t-value, Hollstein t-value, Gleichläufigkeit (GLK) with Buras-Wilmking 2015 correction
- **AI Image Segmentation** — DeepCS-TRD stub for automatic boundary detection
- **Regional Curve Standardisation (RCS)** — Advanced cambial-age detrending
- **COFECHA-Style Quality Control** — Sliding correlation reports for finding dating errors
- **Interactive Chronology Builder** — Real-time EPS and R-bar metrics while building your master curve
- **Geometric Pith Estimator** — Visual tool to estimate missing distances to the pith
- **Standard export** — Write to .rwl, .xml, and automatically generate R scripts (`dplR`)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/fritts.git
cd fritts

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Usage

```bash
# Launch the application
fritts

# Or run directly
python -m dendro.main
```

## Supported Formats

| Format | Extensions | Read | Write |
|--------|-----------|------|-------|
| Tucson Decadal | .rwl, .tuc, .crn | ✅ | ✅ |
| Heidelberg | .fh | ✅ | — |
| TRiDaS | .xml | ✅ | ✅ |

## Target Users

- Dendrochronologists dating archaeological timbers
- Climate researchers building proxy records from tree rings
- Wood specialists in archaeology and heritage

## Tech Stack

- **GUI**: PyQt6
- **Visualization**: PyQtGraph (75–150× faster than Matplotlib for interactive use)
- **Data**: Pandas, NumPy, SciPy
- **AI**: PyTorch
- **XML**: lxml

## License

MIT
