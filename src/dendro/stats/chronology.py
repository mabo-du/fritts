"""chronology.py — Master chronology building from multiple tree-ring series.

exports:
    build_chronology(series_list, method) -> tuple[RingWidthSeries, pd.Series]
    tukey_biweight_mean(values) -> float
used_by:
    dendro.stats.__init__ → re-exports public API
    dendro.ui.stats_panel → ChronologyPanel calls build_chronology
    dendro.ui.main_window → build-chronology action
rules:
    - Default method is 'robust_mean' (Tukey bi-weight); 'simple_mean' as fallback.
    - Returned RingWidthSeries has series_id='CHRONOLOGY', is_reference=True.
    - Sample depth is tracked per year as a separate pd.Series.
    - All series are aligned by astronomical calendar year.
"""

from __future__ import annotations


import numpy as np
import pandas as pd

from dendro.models.series import RingWidthSeries

# ------------------------------------------------------------------ #
# Constants
# ------------------------------------------------------------------ #

_BIWEIGHT_C: float = 9.0
"""Tuning constant for Tukey's bi-weight robust mean (standard in dendro)."""

_BIWEIGHT_MAX_ITER: int = 50
"""Maximum iterations for bi-weight convergence."""

_BIWEIGHT_TOL: float = 1e-6
"""Convergence tolerance for bi-weight iteration."""


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #


def build_chronology(
    series_list: list[RingWidthSeries],
    method: str = "robust_mean",
) -> tuple[RingWidthSeries, pd.Series]:
    """Build a master chronology from a list of tree-ring series.

    All series are aligned by calendar year into a matrix.  A yearly
    central-tendency value is computed using either Tukey's bi-weight
    robust mean (``'robust_mean'``) or a simple arithmetic mean
    (``'simple_mean'``).

    Parameters
    ----------
    series_list : list[RingWidthSeries]
        Individual measurement series to combine.  Must contain at
        least one series.
    method : {'robust_mean', 'simple_mean'}
        Aggregation method.

    Returns
    -------
    tuple[RingWidthSeries, pd.Series]
        ``(chronology, sample_depth)`` where *chronology* is a
        ``RingWidthSeries`` with ``series_id='CHRONOLOGY'`` and
        ``is_reference=True``, and *sample_depth* is a year-indexed
        ``pd.Series`` counting non-NaN contributors per year.

    Raises
    ------
    ValueError
        If *series_list* is empty or *method* is unrecognised.

    Rules:
        - metadata includes: method, n_series, min_depth, max_depth.
        - Years with zero contributing series get NaN in the chronology.
    """
    if not series_list:
        raise ValueError("series_list must contain at least one series.")

    valid_methods = ("robust_mean", "simple_mean")
    if method not in valid_methods:
        raise ValueError(
            f"Unknown method '{method}'. Must be one of {valid_methods}."
        )

    # ---- Align all series by calendar year into a DataFrame ----
    all_pd: list[pd.Series] = [s.to_series() for s in series_list]
    aligned = pd.concat(all_pd, axis=1)  # columns = series, index = years
    aligned.sort_index(inplace=True)

    # ---- Sample depth (count of non-NaN per year) ----
    depth: pd.Series = aligned.notna().sum(axis=1).astype(int)
    depth.index.name = "year"
    depth.name = "sample_depth"

    # ---- Compute yearly chronology values ----
    years = aligned.index.values.astype(np.int64)
    values = np.empty(len(years), dtype=np.float64)

    for i in range(len(years)):
        row = aligned.iloc[i].values.astype(np.float64)
        finite = row[np.isfinite(row)]

        if len(finite) == 0:
            values[i] = np.nan
        elif method == "robust_mean":
            values[i] = tukey_biweight_mean(finite)
        else:  # simple_mean
            values[i] = float(np.mean(finite))

    # ---- Build result objects ----
    start_year = int(years[0])
    depth_int = depth.values.astype(int)
    min_depth = int(np.min(depth_int))
    max_depth = int(np.max(depth_int))

    chronology = RingWidthSeries(
        series_id="CHRONOLOGY",
        start_year=start_year,
        widths=values,
        metadata={
            "method": method,
            "n_series": len(series_list),
            "min_depth": min_depth,
            "max_depth": max_depth,
        },
        is_reference=True,
    )

    return chronology, depth


# ------------------------------------------------------------------ #
# Tukey bi-weight robust mean
# ------------------------------------------------------------------ #


def tukey_biweight_mean(values: np.ndarray) -> float:
    """Compute Tukey's bi-weight robust mean.

    An iterative M-estimator of location that down-weights observations
    far from the centre, using the median as the initial estimate and
    the MAD (median absolute deviation) as the scale.

    Parameters
    ----------
    values : np.ndarray
        1-D array of finite numeric values.

    Returns
    -------
    float
        Robust location estimate.  Falls back to the median if the
        MAD is zero (all values identical or nearly so).

    Rules:
        - Tuning constant c = 9.0 (dendrochronological standard).
        - Converges when absolute change < 1e-6 or after 50 iterations.
        - Input must contain only finite values (no NaN/inf).
    """
    x = np.asarray(values, dtype=np.float64)

    if len(x) == 0:
        return np.nan
    if len(x) == 1:
        return float(x[0])

    # Initial estimate: median
    t_est = float(np.median(x))

    for _ in range(_BIWEIGHT_MAX_ITER):
        # MAD scale
        deviations = x - t_est
        mad = float(np.median(np.abs(deviations)))

        if mad < 1e-15:
            # All values are (nearly) identical — median is the answer
            return t_est

        # Normalised residuals
        u = deviations / (_BIWEIGHT_C * mad)

        # Weights: zero for |u| >= 1
        mask = np.abs(u) < 1.0
        if not np.any(mask):
            # All points are outliers relative to current estimate — fall back
            return t_est

        u_masked = u[mask]
        x_masked = x[mask]
        w = (1.0 - u_masked**2) ** 2

        # Weighted mean
        t_new = float(np.sum(w * x_masked) / np.sum(w))

        if abs(t_new - t_est) < _BIWEIGHT_TOL:
            return t_new

        t_est = t_new

    return t_est

# ------------------------------------------------------------------ #
# Chronology Quality Metrics
# ------------------------------------------------------------------ #

def calculate_rbar(series_list: list[RingWidthSeries]) -> float:
    """Calculate the mean inter-series correlation (R-bar).
    
    This computes the Pearson correlation matrix between all pairs of
    series (where they overlap), and returns the mean of the upper triangle.
    Uses detrended indices if available, falling back to raw widths.
    """
    if len(series_list) < 2:
        return 0.0
        
    all_pd = []
    for s in series_list:
        data = s.indices if s.indices is not None else s.widths
        all_pd.append(pd.Series(data, index=s.years))
        
    aligned = pd.concat(all_pd, axis=1)
    
    # Calculate correlation matrix (pairwise deletion of NaNs)
    corr_matrix = aligned.corr(method='pearson').values
    
    # Extract upper triangle without diagonal
    n = len(series_list)
    upper_tri = corr_matrix[np.triu_indices(n, k=1)]
    
    # Remove NaNs (where pairs had no overlap)
    valid_corrs = upper_tri[~np.isnan(upper_tri)]
    
    if len(valid_corrs) == 0:
        return 0.0
        
    return float(np.mean(valid_corrs))

def calculate_eps(n_trees: int, rbar: float) -> float:
    """Calculate the Expressed Population Signal (EPS).
    
    EPS = (n * rbar) / (1 + (n - 1) * rbar)
    Threshold for a 'good' chronology is typically >= 0.85.
    """
    if n_trees <= 0:
        return 0.0
    
    denominator = 1 + (n_trees - 1) * rbar
    if denominator == 0:
        return 0.0
        
    return (n_trees * rbar) / denominator
