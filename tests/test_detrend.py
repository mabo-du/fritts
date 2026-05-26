import numpy as np
from dendro.stats.detrend import detrend_series

def test_detrend_mean():
    widths = np.array([1.0, 2.0, 3.0, 4.0])
    rwi = detrend_series(widths, method='mean')
    
    # Mean is 2.5, RWI = widths / 2.5
    expected = widths / 2.5
    np.testing.assert_allclose(rwi, expected)

def test_detrend_neg_exp():
    # Construct a perfect negative exponential
    # y = 5.0 * exp(-0.1 * x) + 0.5
    x = np.arange(1, 51)
    widths = 5.0 * np.exp(-0.1 * x) + 0.5
    
    rwi = detrend_series(widths, method='neg_exp')
    
    # Since it's a perfect fit, all RWIs should be exactly 1.0
    np.testing.assert_allclose(rwi, np.ones(50), rtol=1e-3)

def test_detrend_spline():
    # Construct some wavy data
    x = np.arange(1, 101)
    widths = 2.0 + np.sin(x / 10.0)
    
    rwi = detrend_series(widths, method='spline', stiffness=1.0)
    
    # Ensure RWI oscillates roughly around 1.0
    assert np.isclose(np.mean(rwi), 1.0, atol=0.1)
    
    # Spline fit should smooth out the variations
    # the actual RWI should not just be flat 1.0 unless stiffness is very low
    assert np.var(rwi) > 0.01

def test_detrend_nans():
    widths = np.array([1.0, 2.0, np.nan, 4.0])
    rwi = detrend_series(widths, method='mean')
    
    # Mean of valid is (1+2+4)/3 = 2.333...
    assert np.isclose(rwi[0], 1.0 / (7/3))
    assert np.isclose(rwi[1], 2.0 / (7/3))
    assert np.isnan(rwi[2])
    assert np.isclose(rwi[3], 4.0 / (7/3))
