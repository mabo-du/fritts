"""dendro.io.tucson — Parser and writer for the Tucson decadal (.rwl) format.

exports: read_tucson, write_tucson
used_by:
  dendro.ui.dialogs -> ImportDialog, ExportDialog
rules:
  - read_tucson must return list[RingWidthSeries]
  - Missing values (-8 or 0) converted to NaN.
  - Auto-detects precision based on stop code (999 or -9999).
"""

import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)

def read_tucson(filepath: str | Path) -> list[RingWidthSeries]:
    """Parse a Tucson decadal file and return a list of RingWidthSeries."""
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Intermediate storage: series_id -> dict of year -> width
    series_data = defaultdict(dict)
    series_stop_codes = {}
    
    for line_idx, line in enumerate(lines):
        line = line.rstrip("\n\r")
        if not line or len(line) < 12:
            continue
            
        series_id = line[0:8].strip()
        year_str = line[8:12].strip()
        
        try:
            # Handle float values in year column
            year = int(float(year_str))
        except ValueError:
            logger.debug(f"Skipping line {line_idx+1} in {filepath.name}: invalid year '{year_str}'")
            continue
            
        if year < 0:
            logger.warning(f"Negative year {year} found. Ensure correct BCE convention is used.")

        # Read up to 10 width values
        for i in range(10):
            col_start = 12 + i * 6
            col_end = col_start + 6
            if col_end > len(line):
                width_str = line[col_start:]
            else:
                width_str = line[col_start:col_end]
                
            width_str = width_str.strip()
            if not width_str:
                break
                
            try:
                width_val = float(width_str)
            except ValueError:
                continue

            # Detect stop codes
            if width_val == 999.0 or width_val == -9999.0:
                if series_id not in series_stop_codes:
                    series_stop_codes[series_id] = width_val
                break
                
            # Replace missing values (-8 or 0) with NaN
            if width_val == -8.0 or width_val == 0.0:
                width_val = np.nan
                
            series_data[series_id][year + i] = width_val
            
    # Reconstruct RingWidthSeries objects
    result = []
    for series_id, years_data in series_data.items():
        if not years_data:
            continue
            
        min_year = min(years_data.keys())
        max_year = max(years_data.keys())
        
        # Build array of widths
        length = max_year - min_year + 1
        widths = np.full(length, np.nan, dtype=np.float64)
        
        for year, width in years_data.items():
            widths[year - min_year] = width
            
        # Determine precision based on stop code
        stop_code = series_stop_codes.get(series_id, 999.0)
        if stop_code == -9999.0:
            widths = widths / 1000.0  # 0.001mm precision
        else:
            widths = widths / 100.0   # 0.01mm precision
            
        series = RingWidthSeries(
            series_id=series_id,
            start_year=min_year,
            widths=widths
        )
        result.append(series)
        
    return result

def write_tucson(series_list: list[RingWidthSeries], filepath: str | Path, precision: str = '0.01mm') -> None:
    """Write a list of RingWidthSeries to a Tucson decadal file."""
    filepath = Path(filepath)
    
    stop_code = 999 if precision == '0.01mm' else -9999
    multiplier = 100.0 if precision == '0.01mm' else 1000.0
    
    with open(filepath, "w", encoding="utf-8") as f:
        for series in series_list:
            series_id = series.series_id[:8].rjust(8)
            start_year = series.start_year
            
            # Map of year -> value
            year_val_map = {}
            for idx, w in enumerate(series.widths):
                year_val_map[start_year + idx] = w
                
            # Add stop code at end_year + 1
            year_val_map[series.end_year + 1] = "STOP"
            
            min_year = start_year
            max_year = series.end_year + 1
            
            decade_start = (min_year // 10) * 10
            
            for decade in range(decade_start, max_year + 1, 10):
                line = f"{series_id}{decade:4d}"
                has_data = False
                for i in range(10):
                    yr = decade + i
                    if yr in year_val_map:
                        has_data = True
                        val = year_val_map[yr]
                        if val == "STOP":
                            line += f"{stop_code:6d}"
                        else:
                            if np.isnan(val):
                                int_val = -8 if precision == '0.01mm' else 0
                                line += f"{int_val:6d}"
                            else:
                                int_val = int(round(val * multiplier))
                                line += f"{int_val:6d}"
                if has_data:
                    f.write(line + "\n")
