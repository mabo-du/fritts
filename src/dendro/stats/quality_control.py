"""quality_control.py — COFECHA-style sliding correlation quality control.

exports: run_cofecha_check
used_by:
  dendro.ui.qc_dialog -> run_cofecha_check
rules:
  - Perform sliding correlation on detrended indices, not raw widths.
  - Flag segments with r < 0.32 (approx 99% confidence level for n=50).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)


def run_cofecha_check(
    series_list: list["RingWidthSeries"], 
    segment_length: int = 50, 
    overlap: int = 25, 
    critical_r: float = 0.32
) -> str:
    """Run a COFECHA-style sliding correlation analysis to find dating errors.
    
    Args:
        series_list: List of RingWidthSeries objects (must have indices).
        segment_length: Length of the sliding window in years.
        overlap: Overlap between adjacent windows.
        critical_r: Pearson r threshold for flagging a segment as problematic.
        
    Returns:
        A formatted text report detailing problematic segments.
    """
    if len(series_list) < 2:
        return "QC Error: At least two series are required for cross-checking."
        
    # Check that detrending has occurred
    for s in series_list:
        if s.indices is None:
            return "QC Error: All series must be detrended (Analysis -> Detrend) before running Quality Control."

    report = ["=== COFECHA-Style Quality Control Report ==="]
    report.append(f"Segment Length: {segment_length} years")
    report.append(f"Lag Overlap: {overlap} years")
    report.append(f"Critical Threshold (r): {critical_r}\n")
    
    # Pre-align all series into a matrix to easily build master chronologies
    min_year = min(s.start_year for s in series_list)
    max_year = max(s.end_year for s in series_list)
    total_years = max_year - min_year + 1
    
    # Columns are years, Rows are series
    data = np.full((len(series_list), total_years), np.nan)
    for i, s in enumerate(series_list):
        offset = s.start_year - min_year
        data[i, offset:offset + len(s.indices)] = s.indices
        
    problems_found = 0
    
    for i, s in enumerate(series_list):
        # Leave-one-out Master Chronology
        # Average all OTHER series
        other_data = np.delete(data, i, axis=0)
        with np.warnings.catch_warnings():
            np.warnings.simplefilter("ignore", category=RuntimeWarning)
            master_curve = np.nanmean(other_data, axis=0)
            
        # Sliding windows
        start = s.start_year
        end = s.end_year
        
        series_problems = []
        
        for win_start in range(start, end - segment_length + 2, segment_length - overlap):
            win_end = win_start + segment_length - 1
            if win_end > end:
                win_end = end
                win_start = win_end - segment_length + 1
                
            if win_start < start:
                break
                
            # Extract data for this window
            offset_start = win_start - min_year
            offset_end = win_end - min_year + 1
            
            s_window = data[i, offset_start:offset_end]
            m_window = master_curve[offset_start:offset_end]
            
            # Remove NaNs
            valid = ~(np.isnan(s_window) | np.isnan(m_window))
            if valid.sum() < segment_length * 0.5:
                # Not enough overlap in this window
                continue
                
            r, _ = stats.pearsonr(s_window[valid], m_window[valid])
            
            if r < critical_r:
                series_problems.append((win_start, win_end, r))
                
        if series_problems:
            report.append(f"Series: {s.series_id} ({start}-{end})")
            for win_start, win_end, r in series_problems:
                report.append(f"  Flag: {win_start}-{win_end} | r = {r:.3f}")
            report.append("")
            problems_found += len(series_problems)
            
    if problems_found == 0:
        report.append("No dating problems found! All segments exceed the critical correlation threshold.")
    else:
        report.append(f"Total problematic segments flagged: {problems_found}")
        
    return "\n".join(report)
