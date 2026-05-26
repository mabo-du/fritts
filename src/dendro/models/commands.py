"""commands.py — Command Pattern for undo/redo of all data-mutating operations.

exports: Command, InsertRingCommand, DeleteRingCommand, ShiftSeriesCommand, CommandStack
used_by:
  dendro.models.session → SessionManager uses CommandStack
  dendro.ui.main_window → Undo/Redo menu actions
  dendro.ui.series_view → phantom ring insert/delete
rules:
  - Every mutation to RingWidthSeries data MUST be encapsulated as a Command.
  - Commands operate on SessionManager, not directly on series.
  - CommandStack emits Qt signals on state change for UI binding.
  - Maximum stack depth is configurable (default 200).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from dendro.models.session import SessionManager


class Command(ABC):
    """Abstract base class for all undoable commands.

    Rules:
        - execute() and undo() must be fully symmetric — undo(execute(state)) == state.
        - Commands store only the minimal diff needed for reversal.
    """

    @abstractmethod
    def execute(self, session: SessionManager) -> None:
        """Apply the command to the session."""

    @abstractmethod
    def undo(self, session: SessionManager) -> None:
        """Reverse the command."""

    @abstractmethod
    def description(self) -> str:
        """Human-readable description for the Edit menu."""


class InsertRingCommand(Command):
    """Insert a phantom ring (or measured ring) at a specific year in a series.

    Rules:
        - Inserting pushes all subsequent rings forward by one year.
        - Default width is 0.0 (phantom ring); NaN means missing.
    """

    def __init__(self, series_id: str, year: int, width: float = 0.0) -> None:
        self._series_id = series_id
        self._year = year
        self._width = width

    def execute(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        updated = series.with_ring_inserted(self._year, self._width)
        session.replace_series(self._series_id, updated)

    def undo(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        updated = series.with_ring_deleted(self._year)
        session.replace_series(self._series_id, updated)

    def description(self) -> str:
        return f"Insert ring at year {self._year} in '{self._series_id}'"


class DeleteRingCommand(Command):
    """Delete a ring at a specific year in a series.

    Rules:
        - Deleting pulls all subsequent rings backward by one year.
        - Stores the deleted width for undo restoration.
    """

    def __init__(self, series_id: str, year: int) -> None:
        self._series_id = series_id
        self._year = year
        self._deleted_width: float = np.nan  # stored on execute

    def execute(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        idx = self._year - series.start_year
        self._deleted_width = float(series.widths[idx])
        updated = series.with_ring_deleted(self._year)
        session.replace_series(self._series_id, updated)

    def undo(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        updated = series.with_ring_inserted(self._year, self._deleted_width)
        session.replace_series(self._series_id, updated)

    def description(self) -> str:
        return f"Delete ring at year {self._year} in '{self._series_id}'"


class ShiftSeriesCommand(Command):
    """Shift a series forward or backward in time by a given offset.

    Rules:
        - Only changes start_year; ring widths are untouched.
        - offset can be positive (shift forward) or negative (shift backward).
    """

    def __init__(self, series_id: str, offset: int) -> None:
        self._series_id = series_id
        self._offset = offset

    def execute(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        updated = series.shifted(self._offset)
        session.replace_series(self._series_id, updated)

    def undo(self, session: SessionManager) -> None:
        series = session.get_series(self._series_id)
        updated = series.shifted(-self._offset)
        session.replace_series(self._series_id, updated)

    def description(self) -> str:
        direction = "forward" if self._offset > 0 else "backward"
        return f"Shift '{self._series_id}' {abs(self._offset)} year(s) {direction}"


class CommandStack(QObject):
    """Manages the undo/redo history stack.

    Rules:
        - Maximum depth is configurable; oldest commands are discarded when exceeded.
        - Executing a new command clears the redo stack.
        - Emits signals on every state change for UI button enable/disable.
    """

    state_changed = pyqtSignal()  # Emitted after any execute/undo/redo

    def __init__(self, session: SessionManager, max_depth: int = 200) -> None:
        super().__init__()
        self._session = session
        self._max_depth = max_depth
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def execute(self, command: Command) -> None:
        """Execute a command, pushing it onto the undo stack."""
        command.execute(self._session)
        self._undo_stack.append(command)
        self._redo_stack.clear()
        # Enforce max depth
        if len(self._undo_stack) > self._max_depth:
            self._undo_stack.pop(0)
        self.state_changed.emit()

    def undo(self) -> None:
        """Undo the most recent command."""
        if not self.can_undo:
            return
        command = self._undo_stack.pop()
        command.undo(self._session)
        self._redo_stack.append(command)
        self.state_changed.emit()

    def redo(self) -> None:
        """Redo the most recently undone command."""
        if not self.can_redo:
            return
        command = self._redo_stack.pop()
        command.execute(self._session)
        self._undo_stack.append(command)
        self.state_changed.emit()

    def clear(self) -> None:
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.state_changed.emit()

    # ------------------------------------------------------------------ #
    # State queries
    # ------------------------------------------------------------------ #

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """Description of the next command to be undone."""
        if self._undo_stack:
            return self._undo_stack[-1].description()
        return ""

    @property
    def redo_description(self) -> str:
        """Description of the next command to be redone."""
        if self._redo_stack:
            return self._redo_stack[-1].description()
        return ""
