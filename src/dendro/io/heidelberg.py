"""dendro.io.heidelberg — Parser for the Heidelberg (.fh) format.

exports: read_heidelberg
used_by:
  dendro.ui.dialogs -> ImportDialog
rules:
  - read_heidelberg must return list[RingWidthSeries]
  - Auto-detects data layout (single column vs decadal blocks).
  - Handles missing header fields gracefully.
"""

import logging
import re
from pathlib import Path

import numpy as np

from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)

def read_heidelberg(filepath: str | Path) -> list[RingWidthSeries]:
    """Parse a Heidelberg (.fh) file and return a list of RingWidthSeries."""
    filepath = Path(filepath)
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        
    result = []
    
    in_header = False
    in_data = False
    
    metadata = {}
    series_id = ""
    start_year = 0
    widths_list = []
    
    def finish_series():
        nonlocal result, metadata, series_id, start_year, widths_list
        if widths_list:
            if not series_id:
                series_id = f"Series_{len(result)+1}"
            widths = np.array(widths_list, dtype=np.float64) / 100.0  # Heidelberg is typically 1/100mm
            series = RingWidthSeries(
                series_id=series_id,
                start_year=start_year,
                widths=widths,
                metadata=metadata.copy()
            )
            result.append(series)
            
        metadata = {}
        series_id = ""
        start_year = 0
        widths_list = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line == "HEADER:":
            finish_series()
            in_header = True
            in_data = False
            continue
            
        if line == "DATA:":
            in_header = False
            in_data = True
            continue
            
        if in_header:
            match = re.match(r"^([A-Za-z0-9_]+)=(.*)$", line)
            if match:
                key = match.group(1).strip()
                val = match.group(2).strip()
                if key == "KeyCode":
                    series_id = val
                elif key == "DateBegin":
                    try:
                        start_year = int(val)
                    except ValueError:
                        pass
                else:
                    metadata[key] = val
                    
        elif in_data:
            # Try to parse widths
            # Can be decadal or single column
            # E.g. "  123   145   200" or just "123"
            parts = line.split()
            for p in parts:
                try:
                    w = float(p)
                    widths_list.append(w)
                except ValueError:
                    pass
                    
    finish_series()
    return result
