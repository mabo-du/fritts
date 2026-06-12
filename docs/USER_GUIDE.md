# Fritts User Guide

A comprehensive guide to using Fritts for tree-ring cross-dating, measurement, and master chronology building.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Importing Data](#2-importing-data)
3. [The Interface](#3-the-interface)
4. [Working with Series](#4-working-with-series)
5. [Cross-Dating](#5-cross-dating)
6. [Detrending](#6-detrending)
7. [Chronology Building](#7-chronology-building)
8. [ITRDB Data Search](#8-itrdb-data-search)
9. [Quality Control](#9-quality-control)
10. [Exporting Data](#10-exporting-data)
11. [Image Measurement](#11-image-measurement)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Getting Started

### System Requirements

- **OS**: Linux, macOS, or Windows
- **Python**: 3.10 or later
- **RAM**: 4 GB minimum (8 GB recommended for large datasets)
- **Display**: 1280×720 minimum (1920×1080 recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/mabo-du/fritts.git
cd fritts

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install Fritts with dev dependencies
pip install -e ".[dev]"
```

### Launching

```bash
fritts
```

Or directly:

```bash
python -m dendro.main
```

### First Launch

When Fritts starts, you will see a dark-themed main window with:

- A **Series List** panel on the left showing loaded ring-width series
- A **Plot Area** in the centre for visualising series
- A **Stats Panel** on the right showing selected-series statistics
- A **Toolbar** and **Menu Bar** at the top
- A **Status Bar** at the bottom with cursor position and context info

---

## 2. Importing Data

Fritts supports three standard dendrochronology formats:

### Supported Formats

| Format       | Extensions        | Read | Write | Description                          |
|--------------|-------------------|------|-------|--------------------------------------|
| Tucson Decadal | .rwl, .tuc, .crn | ✅   | ✅    | Most common tree-ring format         |
| Heidelberg   | .fh               | ✅   | —     | German format, 1/100mm precision     |
| TRiDaS       | .xml              | ✅   | ✅    | International standard (Tucson subset)|

### Import Steps

1. Click **File > Import** or press `Ctrl+I`.
2. Select one or more files (use `Ctrl+Click` for multiple).
3. Choose the format (auto-detected from extension).
4. Click **Open**.
5. The series appear in the Series List panel.

Files can also be dragged and dropped onto the main window (if supported by your platform).

---

## 3. The Interface

### Main Window Layout

```
┌──────────────┬──────────────────────────────────┬──────────────┐
│  Series List │         Plot Area                │  Stats Panel  │
│              │   (PyQtGraph canvas)             │              │
│  ┌────────┐  │   ┌────────────────────────┐    │  ┌────────┐  │
│  │Series 1│  │   │                        │    │  │Mean:   │  │
│  │Series 2│  │   │   Ring-width curves    │    │  │Std:    │  │
│  │Series 3│  │   │                        │    │  │Range:  │  │
│  └────────┘  │   └────────────────────────┘    │  └────────┘  │
│              │                                  │              │
└──────────────┴──────────────────────────────────┴──────────────┘
│ Status Bar │  Series: 3 loaded  |  Year: 1850  |  Width: 1.24 │
└────────────────────────────────────────────────────────────────┘
```

### Menu Bar

| Menu       | Key Actions                                                  |
|------------|--------------------------------------------------------------|
| **File**   | Import (`Ctrl+I`), Export (`Ctrl+E`), Preferences, Quit      |
| **Edit**   | Undo (`Ctrl+Z`), Redo (`Ctrl+Shift+Z`)                      |
| **View**   | Toggle panels, Zoom to fit (`Ctrl+0`), Reset view            |
| **Tools**  | Cross-Date (`Ctrl+D`), Detrend, Build Chronology, QC Report  |
|            | Search ITRDB, Image Measurement                              |
| **Help**   | About, User Guide                                             |

### Toolbar

Quick-access buttons for: Import, Export, Cross-Date, Detrend, and Chronology Builder.

### Plot Controls

| Control | Action |
|---------|--------|
| **Left-click + drag** | Pan the plot |
| **Scroll wheel** | Zoom in/out |
| **Right-click** | Context menu (toggle series visibility) |
| **Ctrl+Scroll** | Zoom X-axis only |
| **Shift+Scroll** | Zoom Y-axis only |

---

## 4. Working with Series

### Series List Panel

The Series List shows all loaded series with checkboxes to toggle visibility on the plot.

- **Click** a series to select it and show its statistics
- **Double-click** to rename
- **Right-click** for context menu: Remove, Duplicate, Shift, Properties

### Shifting Series

To align a series in time:

1. Select the series in the Series List.
2. Use the **Shift** tool (right-click > Shift, or via toolbar).
3. Enter a positive value to shift right (later), negative to shift left (earlier).
4. The plot updates immediately.

All shifts are tracked in the undo stack (`Ctrl+Z` to revert).

### Series Properties

Each series contains:

- **Series ID**: Unique identifier (editable)
- **Start Year**: First year of measurement
- **End Year**: Last year of measurement
- **Widths Array**: Ring-width measurements
- **Metadata**: Species, site, investigator, etc. (editable in Properties)

---

## 5. Cross-Dating

Fritts provides several statistical cross-dating methods to compare and synchronise ring-width series.

### Opening Cross-Dating

Go to **Tools > Cross-Date** or press `Ctrl+D`.

### Methods

| Method | Description | Range |
|--------|-------------|-------|
| **Baillie-Pilcher t-value** | Standard correlation t-test between series | t > 3.5 = significant |
| **Hollstein t-value** | Weighted cross-dating statistic | t > 3.5 = significant |
| **Gleichläufigkeit (GLK)** | Percentage of agreement in year-to-year trend | > 60% = significant |
| **GLK (Buras-Wilmking)** | Corrected GLK accounting for autocorrelation | More conservative |

### Workflow

1. Select a **Reference Series** (the master or well-dated series).
2. Select one or more **Target Series** to date.
3. Set the overlap threshold (minimum years of overlap required).
4. Click **Run Analysis**.
5. Results display in a table with correlation values and significance.

### Interpreting Results

- **High t-value** (> 3.5): Strong match, series likely correctly dated
- **Moderate t-value** (2.5–3.5): Possible match, investigate further
- **Low t-value** (< 2.5): Weak match, series may be misdated
- **GLK > 60%**: Good trend agreement
- **GLK > 70%**: Very strong trend agreement

### Visual Adjustment

After cross-dating, use the **Adjust Offset** feature to apply the suggested shift and visually confirm the alignment on the plot.

---

## 6. Detrending

Detrending removes biological growth trends to produce standardised indices for chronology building.

### Opening Detrending

Go to **Tools > Detrend**.

### Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **Mean** | Divides by the series mean | Simple standardisation |
| **Negative Exponential** | Fits a negative exponential curve | Most tree-ring series |
| **Spline** | Flexible cubic spline with variable stiffness | Preserving low-frequency signals |

### Workflow

1. Select one or more series to detrend (or leave empty to detrend all).
2. Choose a detrending method.
3. Adjust parameters (e.g., spline stiffness for the spline method).
4. Click **Apply**.
5. New detrended series appear with "[detrended]" in their names.

### Notes

- Detrended series have mean = 1.0 (ring-width indices)
- The original series are not modified
- Multiple detrending methods can be applied sequentially
- Detrended series can be used in chronology building

---

## 7. Chronology Building

The Chronology Builder creates a master chronology from multiple series.

### Opening

Go to **Tools > Build Chronology**.

### Workflow

1. Select which series to include (checkboxes).
2. Choose the averaging method:
   - **Mean**: Arithmetic mean of indices
   - **Biweight Robust Mean**: Resistant to outliers (recommended)
3. Set EPS and R-bar calculation options.
4. Click **Build**.

### Output

The chronology appears in the Series List as "Chronology" with these metrics:

- **EPS (Expressed Population Signal)**: How well the chronology represents the hypothetical population (target > 0.85)
- **R-bar**: Average interseries correlation (higher = better coherence)
- **Number of series**: Contributing series per year
- **Standard deviation**: Variability of the chronology

These metrics update in real-time as you add or remove series.

### Export

Export the chronology via **File > Export** as .crn or .xml.

---

## 8. ITRDB Data Search

Fritts can search and download data directly from the [NOAA International Tree-Ring Data Bank](https://www.ncei.noaa.gov/products/paleoclimatology/tree-ring).

### Opening

Go to **Tools > Search ITRDB**.

### Searching

1. Enter a keyword (e.g., "oak", "colorado pine", "douglas fir").
2. Click **Search** (or press Enter).
3. Results appear in a table with: Study Name, Site, Species, Investigator, Date Range.

### Downloading

1. Select a study from the results.
2. Click **Download Selected** to fetch the .rwl data.
3. Downloaded series are automatically added to your workspace.
4. The series are immediately available for plotting and analysis.

### Notes

- An internet connection is required.
- Searches are sent to the NOAA ITRDB API at `https://www.ncei.noaa.gov/access/paleo-search/study/search.json`.
- Large downloads may take a few seconds depending on file size.
- Some studies may not have .rwl files available (e.g., climate reconstructions derived from tree rings).

---

## 9. Quality Control

The QC (Quality Control) tool provides COFECHA-style analysis.

### Opening

Go to **Tools > QC Report**.

### Features

- **Sliding Correlation**: Correlates each series against the master in overlapping segments
- **Flagged Segments**: Identifies segments with poor correlation (potential dating errors)
- **Segment Length**: Adjustable (default 50 years, step 25 years)
- **Critical Threshold**: Adjustable (default 0.50)

### Workflow

1. Select the master chronology.
2. Select one or more series to check.
3. Adjust segment length and step.
4. Click **Run QC**.
5. Review flagged segments and investigate potential errors.

---

## 10. Exporting Data

### Export Formats

| Format | Extensions | Content |
|--------|-----------|---------|
| Tucson Decadal | .rwl | Ring-width measurements |
| TRiDaS | .xml | Measurements + metadata |
| R Script | .R | Analysis script for `dplR` package |

### Export Steps

1. Select the series to export (or chronology).
2. Go to **File > Export** or press `Ctrl+E`.
3. Choose the export format.
4. Select the destination file.
5. Click **Save**.

### R Export

The R export generates a script compatible with the `dplR` package for advanced statistical analysis in R:

```r
# Generated by Fritts
library(dplR)

# Load data
rwl <- read.rwl("exported_data.rwl")

# Summary statistics
summary(rwl)

# Cross-date
series.rwl <- corr.rwl(rwl, n = 50, offset = 25)

# Plot
plot(rwl)
```

---

## 11. Image Measurement

The Image Measurement tool (DeepCS-TRD integration) helps detect ring boundaries from high-resolution wood section images.

### Opening

Go to **Tools > Image Measurement**.

### Workflow

1. Load a wood-section image (JPEG, PNG, TIFF).
2. If needed, adjust the region of interest.
3. Click **Detect Boundaries** to run AI-based ring detection.
4. Review and manually adjust detected boundaries.
5. Extract ring-width measurements from detected boundaries.

### Note

The AI segmentation feature is a stub in the current release and may require additional model weights to function fully.

---

## 12. Troubleshooting

### Application won't start

**Problem**: `fritts` command not found.

**Solution**: Ensure the virtual environment is activated and the package is installed:

```bash
pip install -e .
```

**Problem**: PyQt6 import errors.

**Solution**: Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt install libxcb-cursor0

# Fedora
sudo dnf install qt6-qtbase-gui
```

### ITRDB search fails

**Problem**: "Failed to query ITRDB API" error.

**Solutions**:
- Check your internet connection.
- The NOAA API may be temporarily unavailable — try again later.
- Some search terms may return no results — try broader terms.
- Firewalls or proxies may block the API — check network settings.

### Plot display issues

**Problem**: Plot is blank or not updating.

**Solutions**:
- Check that series have data (select series in the list).
- Try **View > Zoom to Fit** or `Ctrl+0`.
- Ensure the plot panel is not collapsed.
- Restart the application.

### Cross-dating shows no results

**Problem**: Cross-dating returns empty or no significant matches.

**Solutions**:
- Increase the overlap threshold (minimum years).
- Check that series overlap in time range.
- Try a different cross-dating method.
- Ensure series have sufficient length (>30 years recommended).

### Data import fails

**Problem**: Imported file shows no data or causes errors.

**Solutions**:
- Verify the file format extension matches its content.
- Check for non-standard formatting in the file.
- Try opening the file in a text editor to inspect the format.
- For Tucson files, ensure they follow the standard format with header lines.

---

## Getting Help

- **Issues**: Report bugs on [GitHub Issues](https://github.com/mabo-du/fritts/issues)
- **Discussions**: Ask questions on [GitHub Discussions](https://github.com/mabo-du/fritts/discussions)
- **Email**: Contact the maintainers via the GitHub repository

---

*Fritts — Named in honor of Harold C. Fritts (1930–2024), pioneer of dendroclimatology.*
