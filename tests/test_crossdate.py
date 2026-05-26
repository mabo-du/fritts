import numpy as np
from dendro.stats.crossdate import crossdate_sliding, find_best_matches
from dendro.models.series import RingWidthSeries

def test_crossdate():
    np.random.seed(42)
    # Generate random reference widths (always positive)
    ref_widths = np.random.lognormal(mean=0.5, sigma=0.5, size=200)
    ref = RingWidthSeries("REF", 1800, ref_widths, is_reference=True)
    
    # Create sample that is a noisy subset of reference (starts at 1850)
    sample_widths = ref_widths[50:150] * np.random.lognormal(mean=0, sigma=0.1, size=100)
    sample = RingWidthSeries("SAMP", 1900, sample_widths) 
    
    results = crossdate_sliding(sample, ref, min_overlap=50)
    best = find_best_matches(results, n=1)
    
    # The best match should be at 1850
    assert best.index[0] == 1850
