"""src/dendro/stats/detrend.py — Tree-ring detrending and standardization algorithms.
exports: detrend_series(series, method) -> np.ndarray
used_by: ui.detrend_dialog -> detrend_series
rules:
- Handle NaN values gracefully during curve fitting.
- Use robust bounds for curve_fit to prevent Divergence errors on strange growth curves.
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import UnivariateSpline
from typing import TYPE_CHECKING
import logging
import warnings

if TYPE_CHECKING:
    from dendro.models.series import RingWidthSeries

logger = logging.getLogger(__name__)

def _neg_exp(x, a, b, k):
    """Modified negative exponential function: y = a * e^(-b*x) + k"""
    # Prevent overflow
    b = np.clip(b, -10, 10)
    return a * np.exp(-b * x) + k

def _hugershoff(x, a, b, g, d):
    """Hugershoff polynomial: y = a * x^b * e^(-g*x) + d"""
    # x is 1-indexed to prevent log(0) in power if b < 0, but x starts at 1 anyway
    g = np.clip(g, -10, 10)
    return a * (x**b) * np.exp(-g * x) + d

def fit_negative_exponential(widths: np.ndarray) -> np.ndarray:
    """Fit a negative exponential curve and return the expected values."""
    n = len(widths)
    x = np.arange(1, n + 1)
    
    # Filter out NaNs for fitting
    valid = ~np.isnan(widths)
    if valid.sum() < 10:
        logger.warning("Not enough valid rings to fit negative exponential. Returning mean.")
        mean_val = np.nanmean(widths)
        return np.full(n, mean_val if not np.isnan(mean_val) else 1.0)
        
    x_valid = x[valid]
    y_valid = widths[valid]
    
    # Initial guess:
    # a: intercept approx (first value - min value)
    # b: decay rate (small positive number)
    # k: asymptote (min value)
    p0 = [np.nanmax(y_valid[:10]) - np.nanmin(y_valid), 0.01, np.nanmin(y_valid)]
    
    try:
        # Bounds: a >= 0, b >= 0 (decay, not growth), k >= 0 (positive widths)
        bounds = ([0, 0, 0], [np.inf, 10, np.nanmax(y_valid)])
        popt, _ = curve_fit(_neg_exp, x_valid, y_valid, p0=p0, bounds=bounds, maxfev=5000)
        return _neg_exp(x, *popt)
    except Exception as e:
        logger.warning(f"Negative exponential fit failed ({e}). Falling back to linear/mean.")
        # Fallback to mean if optimization fails
        return np.full(n, np.nanmean(widths))

def fit_hugershoff(widths: np.ndarray) -> np.ndarray:
    """Fit a Hugershoff curve and return the expected values."""
    n = len(widths)
    x = np.arange(1, n + 1, dtype=float)
    
    valid = ~np.isnan(widths)
    if valid.sum() < 10:
        mean_val = np.nanmean(widths)
        return np.full(n, mean_val if not np.isnan(mean_val) else 1.0)
        
    x_valid = x[valid]
    y_valid = widths[valid]
    
    # Initial guess
    p0 = [np.nanmean(y_valid), 1.0, 0.01, np.nanmin(y_valid)]
    
    try:
        # a > 0, b > 0 (initial growth), g > 0 (subsequent decay), d >= 0
        bounds = ([0, 0, 0, 0], [np.inf, 10, 10, np.nanmax(y_valid)])
        popt, _ = curve_fit(_hugershoff, x_valid, y_valid, p0=p0, bounds=bounds, maxfev=5000)
        return _hugershoff(x, *popt)
    except Exception as e:
        logger.warning(f"Hugershoff fit failed ({e}). Falling back to negative exponential.")
        return fit_negative_exponential(widths)

def fit_spline(widths: np.ndarray, stiffness: float = 1.0) -> np.ndarray:
    """Fit a cubic smoothing spline.
    stiffness controls the smoothing factor (s). Higher stiffness = flatter curve.
    """
    n = len(widths)
    x = np.arange(1, n + 1)
    
    valid = ~np.isnan(widths)
    if valid.sum() < 5:
        mean_val = np.nanmean(widths)
        return np.full(n, mean_val if not np.isnan(mean_val) else 1.0)
        
    x_valid = x[valid]
    y_valid = widths[valid]
    
    # UnivariateSpline with s controlling smoothing. 
    # s is the sum of squared residuals allowed. 
    # We roughly scale it by variance and stiffness.
    s = len(y_valid) * np.nanvar(y_valid) * stiffness
    
    try:
        spline = UnivariateSpline(x_valid, y_valid, s=s)
        expected = spline(x)
        # Prevent expected values from crossing zero/going negative
        expected[expected <= 0] = 0.01 
        return expected
    except Exception as e:
        logger.warning(f"Spline fit failed ({e}). Falling back to mean.")
        return np.full(n, np.nanmean(widths))

def detrend_series(widths: np.ndarray, method: str = 'spline', **kwargs) -> np.ndarray:
    """
    Detrend raw ring widths into standardized Ring-Width Indices (RWI).
    RWI = Raw Width / Expected Width.
    """
    if method == 'neg_exp':
        expected = fit_negative_exponential(widths)
    elif method == 'hugershoff':
        expected = fit_hugershoff(widths)
    elif method == 'spline':
        expected = fit_spline(widths, stiffness=kwargs.get('stiffness', 1.0))
    elif method == 'mean':
        expected = np.full(len(widths), np.nanmean(widths))
    else:
        raise ValueError(f"Unknown detrending method: {method}")
    
    # Calculate RWI (Division)
    with np.errstate(divide='ignore', invalid='ignore'):
        rwi = widths / expected
    
    # Handle NaNs or infs from division by zero
    rwi[np.isinf(rwi)] = np.nan
    
    return rwi

def rcs_detrend(series_list: list['RingWidthSeries']) -> dict[str, np.ndarray]:
    """
    Perform Regional Curve Standardisation (RCS) on a population of tree rings.
    
    This perfectly aligns all series by their cambial age (i.e. Ring 1, Ring 2) 
    irrespective of their calendar year, calculates a regional expected growth curve,
    and then detrends each individual series against this regional curve.
    
    Args:
        series_list: List of RingWidthSeries to standardise.
        
    Returns:
        dict mapping series_id -> RWI array
    """
    if not series_list:
        return {}
        
    # 1. Find the maximum cambial age across all series
    max_age = max(s.ring_count for s in series_list)
    
    # 2. Align all raw widths by cambial age into a 2D array
    # Rows = cambial age (1 to max_age), Cols = individual series
    aligned = np.full((max_age, len(series_list)), np.nan)
    
    for i, s in enumerate(series_list):
        widths = s.widths
        aligned[:len(widths), i] = widths
        
    # 3. Calculate the Regional Curve (RC)
    # Using robust mean (or median) to resist outliers
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        rc = np.nanmedian(aligned, axis=1)
        
    # Optional: smooth the RC slightly to remove inter-annual noise
    # Since we are using median, a simple spline can smooth the biological trend
    valid_rc = ~np.isnan(rc)
    if valid_rc.sum() > 5:
        # Fit a stiff spline to the RC
        x = np.arange(1, max_age + 1)
        spline = UnivariateSpline(x[valid_rc], rc[valid_rc], s=len(rc)*np.nanvar(rc)*2.0)
        smoothed_rc = spline(x)
        smoothed_rc[smoothed_rc <= 0] = 0.01
    else:
        smoothed_rc = rc

    # 4. Detrend each series against the RC
    results = {}
    for s in series_list:
        expected = smoothed_rc[:len(s.widths)]
        with np.errstate(divide='ignore', invalid='ignore'):
            rwi = s.widths / expected
        rwi[np.isinf(rwi)] = np.nan
        results[s.series_id] = rwi
        
    return results

