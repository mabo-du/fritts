"""session.py — Application state manager holding all loaded ring-width series.

exports: SessionManager
used_by:
  dendro.models.commands → Command.execute/undo operate on SessionManager
  dendro.ui.main_window → MainWindow owns the SessionManager
  dendro.ui.series_view → reads series for plotting
  dendro.ui.series_list → reads series metadata
  dendro.stats.crossdate → reads series for analysis
rules:
  - SessionManager is the single source of truth for all loaded data.
  - Direct series mutation is forbidden — use CommandStack.
  - Qt signals must fire on every data change for UI reactivity.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal

from dendro.models.series import RingWidthSeries


class SessionManager(QObject):
    """Holds all loaded ring-width series and provides aligned data access.

    Signals:
        series_added: Emitted with series_id when a new series is loaded.
        series_removed: Emitted with series_id when a series is removed.
        series_changed: Emitted with series_id when a series is replaced/modified.
        session_cleared: Emitted when all series are removed.

    Rules:
        - All mutations (add/remove/replace) emit the appropriate signal.
        - get_aligned_dataframe() lazily rebuilds the master DataFrame on demand.
    """

    series_added = pyqtSignal(str)
    series_removed = pyqtSignal(str)
    series_changed = pyqtSignal(str)
    session_cleared = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._series: dict[str, RingWidthSeries] = {}
        self._df_cache: pd.DataFrame | None = None

    # ------------------------------------------------------------------ #
    # Series CRUD
    # ------------------------------------------------------------------ #

    def add_series(self, series: RingWidthSeries) -> None:
        """Add a new series to the session.

        Rules:
            - If series_id already exists, raises ValueError.
            - Invalidates the DataFrame cache.
        """
        if series.series_id in self._series:
            raise ValueError(f"Series '{series.series_id}' already exists in the session.")
        self._series[series.series_id] = series
        self._df_cache = None
        self.series_added.emit(series.series_id)

    def remove_series(self, series_id: str) -> RingWidthSeries:
        """Remove and return a series by ID.

        Rules:
            - Raises KeyError if not found.
            - Invalidates the DataFrame cache.
        """
        series = self._series.pop(series_id)
        self._df_cache = None
        self.series_removed.emit(series_id)
        return series

    def replace_series(self, series_id: str, series: RingWidthSeries) -> None:
        """Replace an existing series (used by Command execute/undo).

        Rules:
            - Raises KeyError if series_id not found.
            - The replacement series inherits the same series_id key.
        """
        if series_id not in self._series:
            raise KeyError(f"Series '{series_id}' not found in session.")
        self._series[series_id] = series
        self._df_cache = None
        self.series_changed.emit(series_id)

    def get_series(self, series_id: str) -> RingWidthSeries:
        """Retrieve a series by ID. Raises KeyError if not found."""
        return self._series[series_id]

    def has_series(self, series_id: str) -> bool:
        """Check if a series exists in the session."""
        return series_id in self._series

    def clear(self) -> None:
        """Remove all series from the session."""
        self._series.clear()
        self._df_cache = None
        self.session_cleared.emit()

    # ------------------------------------------------------------------ #
    # Bulk access
    # ------------------------------------------------------------------ #

    @property
    def series_ids(self) -> list[str]:
        """All loaded series IDs in insertion order."""
        return list(self._series.keys())

    @property
    def series_count(self) -> int:
        return len(self._series)

    @property
    def all_series(self) -> list[RingWidthSeries]:
        """All loaded series as a list."""
        return list(self._series.values())

    @property
    def reference_series(self) -> list[RingWidthSeries]:
        """All series marked as reference/master."""
        return [s for s in self._series.values() if s.is_reference]

    @property
    def floating_series(self) -> list[RingWidthSeries]:
        """All series not marked as reference (undated/floating)."""
        return [s for s in self._series.values() if not s.is_reference]

    # ------------------------------------------------------------------ #
    # Aligned DataFrame
    # ------------------------------------------------------------------ #

    def get_aligned_dataframe(self) -> pd.DataFrame:
        """Build a DataFrame with years as rows and series as columns.

        Automatically aligns all series by their calendar years.
        Non-overlapping regions are filled with NaN.

        Rules:
            - Cached and rebuilt only when data changes.
            - Index is int64 calendar years, ascending.
        """
        if self._df_cache is not None:
            return self._df_cache

        if not self._series:
            self._df_cache = pd.DataFrame()
            return self._df_cache

        pd_series_list = [s.to_series() for s in self._series.values()]
        self._df_cache = pd.concat(pd_series_list, axis=1)
        self._df_cache.sort_index(inplace=True)
        return self._df_cache

    def get_overlap_info(
        self, id_a: str, id_b: str
    ) -> dict[str, Any]:
        """Return overlap statistics between two series.

        Returns dict with keys: start_year, end_year, overlap_years, has_overlap.
        """
        a = self._series[id_a]
        b = self._series[id_b]
        overlap_start = max(a.start_year, b.start_year)
        overlap_end = min(a.end_year, b.end_year)
        overlap_years = max(0, overlap_end - overlap_start + 1)
        return {
            "start_year": overlap_start if overlap_years > 0 else None,
            "end_year": overlap_end if overlap_years > 0 else None,
            "overlap_years": overlap_years,
            "has_overlap": overlap_years > 0,
        }
