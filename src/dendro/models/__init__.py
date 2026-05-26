"""dendro.models — Core data structures and application state.

exports: RingWidthSeries, SessionManager, CommandStack
used_by: dendro.io → parsers, dendro.stats → algorithms, dendro.ui → views
rules:
  - RingWidthSeries is the canonical data unit — all parsers produce it.
  - All mutations to series data MUST go through CommandStack for undo/redo.
"""
