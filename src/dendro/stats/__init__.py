"""dendro.stats — Statistical algorithms for cross-dating and chronology building.

exports: crossdate_sliding, compute_t_bp, compute_t_ho, compute_glk, build_chronology
used_by: dendro.ui.stats_panel → StatsPanel, dendro.ui.main_window → analysis actions
rules:
  - All algorithms must be vectorized via NumPy for real-time performance.
  - GLK must use the Buras-Wilmking 2015 corrected computation.
  - Minimum 50-ring overlap for stable results.
"""
