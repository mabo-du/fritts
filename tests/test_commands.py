import numpy as np
from dendro.models.series import RingWidthSeries
from dendro.models.session import SessionManager
from dendro.models.commands import CommandStack, InsertRingCommand, DeleteRingCommand, ShiftSeriesCommand

def test_commands():
    session = SessionManager()
    widths = np.array([1.0, 2.0, 3.0])
    series = RingWidthSeries("TEST", 2000, widths)
    session.add_series(series)
    
    stack = CommandStack(session)
    
    # Insert ring
    cmd1 = InsertRingCommand("TEST", 2001, 1.5)
    stack.execute(cmd1)
    assert len(session.get_series("TEST").widths) == 4
    assert session.get_series("TEST").widths[1] == 1.5
    
    # Undo insert
    stack.undo()
    assert len(session.get_series("TEST").widths) == 3
    assert session.get_series("TEST").widths[1] == 2.0
    
    # Delete ring
    cmd2 = DeleteRingCommand("TEST", 2000)
    stack.execute(cmd2)
    assert len(session.get_series("TEST").widths) == 2
    assert session.get_series("TEST").widths[0] == 2.0
    assert session.get_series("TEST").start_year == 2000
    
    stack.undo()
    assert len(session.get_series("TEST").widths) == 3
    assert session.get_series("TEST").widths[0] == 1.0
    
    # Shift series
    cmd3 = ShiftSeriesCommand("TEST", 10)
    stack.execute(cmd3)
    assert session.get_series("TEST").start_year == 2010
    
    stack.undo()
    assert session.get_series("TEST").start_year == 2000
