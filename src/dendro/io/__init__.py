"""dendro.io — File format parsers and writers for dendrochronology data.

exports: read_tucson, write_tucson, read_heidelberg, read_tridas
used_by: dendro.ui.dialogs → ImportDialog, ExportDialog
rules:
  - Every reader function returns list[RingWidthSeries].
  - Every reader must be fault-tolerant against real-world malformations.
"""

from dendro.io.heidelberg import read_heidelberg
from dendro.io.tridas import read_tridas
from dendro.io.tucson import read_tucson, write_tucson

__all__ = [
    "read_tucson",
    "write_tucson",
    "read_heidelberg",
    "read_tridas",
]
