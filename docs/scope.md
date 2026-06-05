# PROJECT — Fritts

## Overview
An open-source desktop tool for tree-ring cross-dating, measurement, and master chronology building. Existing software is often dated, proprietary, or lacks a modern visual interface.

## Target users
- Dendrochronologists dating archaeological timbers
- Climate researchers building proxy records from tree rings
- Wood specialists in archaeology and heritage

## MVP scope (v1)
- Import standard formats (.rwl, .tuc, .txt) for ring widths
- Interactive visual plotting of ring-width series (zoom, pan, overlay)
- Statistical cross-dating using standard algorithms (correlation, t-test, GLK)
- Visual adjustment: easily shift series backward/forward in time to find the best fit
- Basic master chronology generation (averaging synchronized series)
- Export adjusted series to standard formats (.rwl)

## Feature roadmap (v2+)
- Direct measurement from high-resolution images
- Automated cross-dating suggestions
- Detrending and standardization of growth curves
- Integration with the International Tree-Ring Data Bank (ITRDB) via API

## Tech stack recommendation
- **Language**: Python
- **GUI**: PyQt6
- **Data handling**: Pandas, NumPy, SciPy
- **Visualization**: PyQtGraph
