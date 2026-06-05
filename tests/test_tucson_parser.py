import numpy as np
from dendro.io.tucson import read_tucson, write_tucson
from dendro.models.series import RingWidthSeries

def test_tucson_read_write(tmp_path):
    filepath = tmp_path / "test.rwl"
    
    widths = np.array([1.23, 2.34, 0.0, np.nan, 4.56])
    series = RingWidthSeries("TEST", 2000, widths)
    
    write_tucson([series], filepath, precision='0.01mm')
    
    read_series = read_tucson(filepath)
    assert len(read_series) == 1
    
    s = read_series[0]
    assert s.series_id == "TEST"
    assert s.start_year == 2000
    assert len(s.widths) == 5
    
    np.testing.assert_allclose(s.widths[:2], widths[:2])
    # 0.0 is saved as -8, read back as nan
    assert np.isnan(s.widths[2])
    assert np.isnan(s.widths[3])
    np.testing.assert_allclose(s.widths[4], widths[4])
