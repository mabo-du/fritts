"""series.py — Core data structure representing a single tree-ring measurement series.

exports: RingWidthSeries
used_by:
  dendro.io.tucson → read_tucson produces list[RingWidthSeries]
  dendro.io.heidelberg → read_heidelberg produces list[RingWidthSeries]
  dendro.io.tridas → read_tridas produces list[RingWidthSeries]
  dendro.models.session → SessionManager holds dict of RingWidthSeries
  dendro.stats.crossdate → algorithms operate on RingWidthSeries
  dendro.stats.chronology → build_chronology consumes list[RingWidthSeries]
rules:
  - widths is always a NumPy float64 array; NaN represents missing rings.
  - start_year uses astronomical year numbering (year 0 exists) internally.
  - All mutating methods return new instances or copies — never mutate in place.
    Direct mutation is reserved for Command objects only.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class RingWidthSeries:
    """A single tree-ring width measurement series.

    Attributes:
        series_id: Unique identifier string (e.g., 'OAK01A').
        start_year: First calendar year of the series (astronomical numbering).
        widths: Ring-width values in millimetres as float64.
                NaN indicates a missing or unmeasured ring.
        indices: Optional Ring-Width Indices (RWI) computed via detrending.
                 float64 array of the same length as widths, or None.
        metadata: Arbitrary key-value store for species, sapwood count,
                  site name, lat/lon, etc.
        is_reference: True if this series is a dated reference/master chronology.

    Rules:
        - widths and indices must be 1-D float64 NumPy arrays.
        - Phantom rings are stored as 0.0, missing rings as NaN.
        - end_year is computed, never stored directly.
    """

    series_id: str
    start_year: int
    widths: np.ndarray
    indices: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    is_reference: bool = False

    def __post_init__(self) -> None:
        """Validate and coerce arrays to float64 ndarray."""
        if not isinstance(self.widths, np.ndarray):
            self.widths = np.asarray(self.widths, dtype=np.float64)
        elif self.widths.dtype != np.float64:
            self.widths = self.widths.astype(np.float64)
            
        if self.indices is not None:
            if not isinstance(self.indices, np.ndarray):
                self.indices = np.asarray(self.indices, dtype=np.float64)
            elif self.indices.dtype != np.float64:
                self.indices = self.indices.astype(np.float64)

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def end_year(self) -> int:
        """Last calendar year of the series (inclusive)."""
        return self.start_year + len(self.widths) - 1

    @property
    def ring_count(self) -> int:
        """Total number of rings (including NaN/missing)."""
        return len(self.widths)

    @property
    def measured_count(self) -> int:
        """Number of non-NaN rings."""
        return int(np.count_nonzero(~np.isnan(self.widths)))

    @property
    def years(self) -> np.ndarray:
        """Array of calendar years corresponding to each ring."""
        return np.arange(self.start_year, self.end_year + 1, dtype=np.int64)

    # ------------------------------------------------------------------ #
    # Pandas integration
    # ------------------------------------------------------------------ #

    def to_series(self) -> pd.Series:
        """Return a Pandas Series indexed by calendar year.

        Rules:
            - Index dtype is Int64 (nullable integer).
            - Values are float64 ring widths.
        """
        idx = pd.Index(self.years, dtype="int64", name="year")
        return pd.Series(self.widths.copy(), index=idx, name=self.series_id)

    @classmethod
    def from_series(
        cls,
        s: pd.Series,
        indices: pd.Series | None = None,
        metadata: dict[str, Any] | None = None,
        is_reference: bool = False,
    ) -> RingWidthSeries:
        """Create a RingWidthSeries from a year-indexed Pandas Series."""
        idx_vals = indices.values.astype(np.float64) if indices is not None else None
        return cls(
            series_id=str(s.name),
            start_year=int(s.index.min()),
            widths=s.values.astype(np.float64),
            indices=idx_vals,
            metadata=metadata or {},
            is_reference=is_reference,
        )

    # ------------------------------------------------------------------ #
    # Non-mutating operations (return copies)
    # ------------------------------------------------------------------ #

    def shifted(self, offset: int) -> RingWidthSeries:
        """Return a copy with start_year shifted by *offset* years."""
        idx = self.indices.copy() if self.indices is not None else None
        return RingWidthSeries(
            series_id=self.series_id,
            start_year=self.start_year + offset,
            widths=self.widths.copy(),
            indices=idx,
            metadata=copy.deepcopy(self.metadata),
            is_reference=self.is_reference,
        )

    def with_indices(self, indices: np.ndarray) -> RingWidthSeries:
        """Return a copy with indices assigned."""
        return RingWidthSeries(
            series_id=self.series_id,
            start_year=self.start_year,
            widths=self.widths.copy(),
            indices=indices.copy(),
            metadata=copy.deepcopy(self.metadata),
            is_reference=self.is_reference,
        )

    def with_ring_inserted(self, year: int, width: float = 0.0) -> RingWidthSeries:
        """Return a copy with a ring inserted at *year*.

        If *year* falls within the series span, the new ring is inserted
        before that year's position, pushing subsequent rings forward.
        A width of 0.0 represents a phantom ring.
        """
        if year < self.start_year or year > self.end_year + 1:
            raise ValueError(
                f"Year {year} is outside the insertable range "
                f"[{self.start_year}, {self.end_year + 1}]."
            )
        idx = year - self.start_year
        new_widths = np.insert(self.widths, idx, width)
        new_indices = np.insert(self.indices, idx, np.nan) if self.indices is not None else None
        
        return RingWidthSeries(
            series_id=self.series_id,
            start_year=self.start_year,
            widths=new_widths,
            indices=new_indices,
            metadata=copy.deepcopy(self.metadata),
            is_reference=self.is_reference,
        )

    def with_ring_deleted(self, year: int) -> RingWidthSeries:
        """Return a copy with the ring at *year* removed."""
        if year < self.start_year or year > self.end_year:
            raise ValueError(
                f"Year {year} is outside the series span "
                f"[{self.start_year}, {self.end_year}]."
            )
        idx = year - self.start_year
        new_widths = np.delete(self.widths, idx)
        new_indices = np.delete(self.indices, idx) if self.indices is not None else None
        
        return RingWidthSeries(
            series_id=self.series_id,
            start_year=self.start_year,
            widths=new_widths,
            indices=new_indices,
            metadata=copy.deepcopy(self.metadata),
            is_reference=self.is_reference,
        )

    # ------------------------------------------------------------------ #
    # Display
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        species = self.metadata.get("species", "unknown")
        return (
            f"RingWidthSeries('{self.series_id}', "
            f"{self.start_year}–{self.end_year}, "
            f"n={self.ring_count}, species={species})"
        )
