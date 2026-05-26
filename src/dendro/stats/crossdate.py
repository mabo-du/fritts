"""crossdate.py — Cross-dating statistical algorithms for dendrochronology.

exports:
    compute_t_bp(sample, reference) -> float
    compute_t_ho(sample, reference) -> float
    compute_glk(sample, reference) -> tuple[float, float, float]
    crossdate_sliding(sample, reference, min_overlap) -> pd.DataFrame
    find_best_matches(results_df, n) -> pd.DataFrame
used_by:
    dendro.stats.__init__ → re-exports public API
    dendro.ui.stats_panel → StatsPanel calls crossdate_sliding
    dendro.ui.main_window → analysis actions
rules:
    - All algorithms must be vectorized via NumPy for real-time performance.
    - GLK must use the Buras-Wilmking 2015 corrected computation.
    - Minimum 50-ring overlap for stable results; return sentinel values below threshold.
    - NaN values in input arrays must be handled gracefully (propagate or skip).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from dendro.models.series import RingWidthSeries

# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #

_MIN_OVERLAP_DEFAULT: int = 50
"""Minimum overlap in years for a statistically meaningful result."""


# ------------------------------------------------------------------ #
# Baillie-Pilcher t-value
# ------------------------------------------------------------------ #


def compute_t_bp(sample: np.ndarray, reference: np.ndarray) -> float:
    """Compute the Baillie-Pilcher t-value between two aligned ring-width arrays.

    The B-P transform applies a 5-year centred running mean to log-transformed
    widths, then divides each log value by the running mean to produce a
    dimensionless *dating index*.  Pearson r on the overlapping indices is
    converted to a Student-t statistic.

    Parameters
    ----------
    sample : np.ndarray
        Sample ring-width values (float64), already aligned to *reference*.
    reference : np.ndarray
        Reference ring-width values (float64), same length as *sample*.

    Returns
    -------
    float
        Baillie-Pilcher t-value.  Returns 0.0 if overlap < 50 or
        computation fails.

    Rules:
        - Input arrays MUST be the same length (pre-aligned overlap).
        - Values ≤ 0 are replaced with NaN before log transform.
        - Returns 0.0 on insufficient data rather than raising.
    """
    n = min(len(sample), len(reference))
    if n < _MIN_OVERLAP_DEFAULT:
        return 0.0

    try:
        # Truncate to equal length
        s = sample[:n].astype(np.float64, copy=True)
        r = reference[:n].astype(np.float64, copy=True)

        # Replace non-positive values with NaN before log
        s[s <= 0] = np.nan
        r[r <= 0] = np.nan

        s_log = np.log(s)
        r_log = np.log(r)

        # 5-year centred running mean via convolution
        kernel = np.ones(5) / 5.0
        s_rm = np.convolve(s_log, kernel, mode="valid")
        r_rm = np.convolve(r_log, kernel, mode="valid")

        # Dating index: log value / running mean (central portion only)
        # mode='valid' removes 2 values from each end → indices [2 .. n-3]
        trim = 2
        s_idx = s_log[trim : n - trim] / s_rm
        r_idx = r_log[trim : n - trim] / r_rm

        # Drop positions where either index is NaN/inf
        valid = np.isfinite(s_idx) & np.isfinite(r_idx)
        s_clean = s_idx[valid]
        r_clean = r_idx[valid]

        n_eff = len(s_clean)
        if n_eff < _MIN_OVERLAP_DEFAULT:
            return 0.0

        return _pearson_to_t(s_clean, r_clean, n_eff)

    except Exception:  # noqa: BLE001 — return sentinel on any failure
        return 0.0


# ------------------------------------------------------------------ #
# Hollstein t-value
# ------------------------------------------------------------------ #


def compute_t_ho(sample: np.ndarray, reference: np.ndarray) -> float:
    """Compute the Hollstein t-value between two aligned ring-width arrays.

    The Hollstein *Wuchswerte* (growth-change) transform converts each
    consecutive pair of rings into a percentage-change index::

        W_i = 100 * 2 * (x_i − x_{i-1}) / (x_i + x_{i-1})

    Division by zero (both rings = 0) sets W_i to 0.  Pearson r on the
    overlapping W-series is converted to a Student-t statistic.

    Parameters
    ----------
    sample : np.ndarray
        Sample ring-width values (float64), already aligned.
    reference : np.ndarray
        Reference ring-width values (float64), same length.

    Returns
    -------
    float
        Hollstein t-value.  Returns 0.0 if overlap < 50 or computation
        fails.

    Rules:
        - Division by zero produces W = 0, NOT NaN.
        - NaN inputs propagate; positions with NaN in either series are
          excluded from the correlation.
    """
    n = min(len(sample), len(reference))
    if n < _MIN_OVERLAP_DEFAULT:
        return 0.0

    try:
        s = sample[:n].astype(np.float64, copy=True)
        r = reference[:n].astype(np.float64, copy=True)

        s_w = _wuchswerte(s)
        r_w = _wuchswerte(r)

        # Drop NaN/inf positions
        valid = np.isfinite(s_w) & np.isfinite(r_w)
        s_clean = s_w[valid]
        r_clean = r_w[valid]

        n_eff = len(s_clean)
        if n_eff < _MIN_OVERLAP_DEFAULT:
            return 0.0

        return _pearson_to_t(s_clean, r_clean, n_eff)

    except Exception:  # noqa: BLE001
        return 0.0


# ------------------------------------------------------------------ #
# GLK — Gleichläufigkeit (Buras-Wilmking 2015)
# ------------------------------------------------------------------ #


def compute_glk(
    sample: np.ndarray,
    reference: np.ndarray,
) -> tuple[float, float, float]:
    """Compute corrected GLK with Z-score and p-value.

    Implements the Buras & Wilmking (2015) correction: year-pairs where
    *either* series shows zero change are *excluded* from scoring, rather
    than counted as semi-synchronous (the legacy error).

    Parameters
    ----------
    sample : np.ndarray
        Sample ring-width values (float64), already aligned.
    reference : np.ndarray
        Reference ring-width values (float64), same length.

    Returns
    -------
    tuple[float, float, float]
        ``(glk, z_score, p_value)``.  Returns ``(0.5, 0.0, 1.0)`` when
        overlap < 50 or no scorable pairs exist.

    Rules:
        - Pairs where either series shows zero change are EXCLUDED.
        - Z-score assumes GLK is asymptotically normal around 0.5.
    """
    n = min(len(sample), len(reference))
    if n < _MIN_OVERLAP_DEFAULT:
        return 0.5, 0.0, 1.0

    try:
        s = sample[:n].astype(np.float64, copy=True)
        r = reference[:n].astype(np.float64, copy=True)

        # Directional change signs (+1, -1, 0)
        s_diff = np.diff(s)
        r_diff = np.diff(r)
        s_sign = np.sign(s_diff)
        r_sign = np.sign(r_diff)

        # Buras-Wilmking: exclude pairs where either sign is 0
        both_nonzero = (s_sign != 0) & (r_sign != 0)

        # Also exclude pairs where either diff is NaN
        both_finite = np.isfinite(s_diff) & np.isfinite(r_diff)
        scorable = both_nonzero & both_finite

        s_scored = s_sign[scorable]
        r_scored = r_sign[scorable]
        n_scored = len(s_scored)

        if n_scored == 0:
            return 0.5, 0.0, 1.0

        synchronous = int(np.sum(s_scored == r_scored))
        glk = synchronous / n_scored

        # Z-score
        std = np.sqrt(1.0 / (4.0 * n_scored))
        z_score = (glk - 0.5) / std if std > 0 else 0.0

        # One-tailed p-value (upper tail)
        p_value = float(sp_stats.norm.sf(z_score))

        return float(glk), float(z_score), float(p_value)

    except Exception:  # noqa: BLE001
        return 0.5, 0.0, 1.0


# ------------------------------------------------------------------ #
# Sliding cross-date
# ------------------------------------------------------------------ #


def crossdate_sliding(
    sample: RingWidthSeries,
    reference: RingWidthSeries,
    min_overlap: int = _MIN_OVERLAP_DEFAULT,
) -> pd.DataFrame:
    """Slide *sample* across *reference* and compute statistics at each offset.

    At every valid position the sample's raw width array is overlaid on
    the reference.  Three statistics are computed on the overlapping
    segment: Baillie-Pilcher t, Hollstein t, and corrected GLK.

    Parameters
    ----------
    sample : RingWidthSeries
        Undated or floating sample series.
    reference : RingWidthSeries
        Dated reference / master chronology.
    min_overlap : int, optional
        Minimum number of overlapping rings required (default 50).

    Returns
    -------
    pd.DataFrame
        Indexed by proposed ``start_year`` for the sample.  Columns:
        ``['t_bp', 't_ho', 'glk', 'z_score', 'p_value', 'overlap']``.
        Only positions meeting *min_overlap* are included.

    Rules:
        - Uses raw NumPy arrays — no pandas rolling.
        - Offset range covers every position where overlap >= min_overlap.
    """
    s_arr = sample.widths
    r_arr = reference.widths
    s_len = len(s_arr)
    r_len = len(r_arr)

    # The proposed start_year range for the sample:
    # earliest: reference.start_year - s_len + min_overlap
    # latest:   reference.end_year - min_overlap + 1
    earliest_start = reference.start_year - s_len + min_overlap
    latest_start = reference.end_year - min_overlap + 1

    rows: list[dict[str, float | int]] = []

    for proposed_start in range(earliest_start, latest_start + 1):
        # Compute the overlapping slice indices
        overlap_begin = max(proposed_start, reference.start_year)
        overlap_end = min(
            proposed_start + s_len - 1,
            reference.end_year,
        )
        overlap_n = overlap_end - overlap_begin + 1

        if overlap_n < min_overlap:
            continue

        # Extract overlapping segments
        s_offset = overlap_begin - proposed_start
        r_offset = overlap_begin - reference.start_year
        s_slice = s_arr[s_offset : s_offset + overlap_n]
        r_slice = r_arr[r_offset : r_offset + overlap_n]

        # Compute statistics
        t_bp = compute_t_bp(s_slice, r_slice)
        t_ho = compute_t_ho(s_slice, r_slice)
        glk, z_score, p_value = compute_glk(s_slice, r_slice)

        rows.append(
            {
                "t_bp": t_bp,
                "t_ho": t_ho,
                "glk": glk,
                "z_score": z_score,
                "p_value": p_value,
                "overlap": overlap_n,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["t_bp", "t_ho", "glk", "z_score", "p_value", "overlap"],
        )

    # Build index from the proposed start years that actually made it
    start_years = list(
        range(earliest_start, latest_start + 1)
    )
    # We need only the years that produced rows — re-derive from the loop
    valid_starts: list[int] = []
    for proposed_start in range(earliest_start, latest_start + 1):
        overlap_begin = max(proposed_start, reference.start_year)
        overlap_end = min(proposed_start + s_len - 1, reference.end_year)
        overlap_n = overlap_end - overlap_begin + 1
        if overlap_n >= min_overlap:
            valid_starts.append(proposed_start)

    idx = pd.Index(valid_starts, name="start_year", dtype="int64")
    return pd.DataFrame(rows, index=idx)


# ------------------------------------------------------------------ #
# Best matches
# ------------------------------------------------------------------ #


def find_best_matches(results_df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return the top *n* cross-dating positions ranked by Baillie-Pilcher t.

    Parameters
    ----------
    results_df : pd.DataFrame
        Output of :func:`crossdate_sliding`.
    n : int, optional
        Number of top results to return (default 10).

    Returns
    -------
    pd.DataFrame
        Subset of *results_df* sorted by ``t_bp`` descending.
    """
    if results_df.empty:
        return results_df.copy()
    return results_df.sort_values("t_bp", ascending=False).head(n)


# ================================================================== #
# Private helpers
# ================================================================== #


def _pearson_to_t(a: np.ndarray, b: np.ndarray, n: int) -> float:
    """Compute Pearson r then convert to Student-t statistic.

    Rules:
        - Returns 0.0 if r² ≈ 1 (perfect correlation edge case) or n < 3.
    """
    if n < 3:
        return 0.0

    r, _ = sp_stats.pearsonr(a, b)

    r_sq = r * r
    denom = 1.0 - r_sq
    if denom <= 0:
        # Perfect or near-perfect correlation — t → ∞; cap at 0.0 sentinel
        # (should not occur in real dendro data).
        return 0.0

    t = r * np.sqrt((n - 2) / denom)
    return float(t)


def _wuchswerte(x: np.ndarray) -> np.ndarray:
    """Hollstein Wuchswerte (growth-change) transform.

    W_i = 100 * 2 * (x_i − x_{i-1}) / (x_i + x_{i-1})

    Division by zero (both rings = 0) produces W_i = 0.
    """
    diff = x[1:] - x[:-1]
    total = x[1:] + x[:-1]

    # Safe divide: where total == 0, set result to 0
    with np.errstate(divide="ignore", invalid="ignore"):
        w = np.where(total != 0, 100.0 * 2.0 * diff / total, 0.0)

    return w
