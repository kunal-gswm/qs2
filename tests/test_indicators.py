import pandas as pd
import numpy as np
import pytest
from bveqse.strategy.indicators import calculate_ema, calculate_atr

def test_ema_matches_formula():
    closes = pd.Series([10.0] * 50 + [11.0, 12.0, 13.0, 14.0])
    ema = calculate_ema(closes, period=50)
    
    assert pd.isna(ema.iloc[48])
    # Bar 50 (index 49) is the seed SMA
    assert ema.iloc[49] == 10.0
    
    alpha = 2.0 / 51.0
    # Next bar EMA
    expected_50 = alpha * 11.0 + (1 - alpha) * 10.0
    np.testing.assert_allclose(ema.iloc[50], expected_50, rtol=1e-9)

def test_atr_matches_formula():
    high = pd.Series([12.0] * 14 + [13.0, 14.0])
    low = pd.Series([8.0] * 14 + [9.0, 10.0])
    close = pd.Series([10.0] * 14 + [11.0, 12.0])
    
    atr = calculate_atr(high, low, close, period=14)
    assert pd.isna(atr.iloc[12])
    # Seed TR is 4.0 for all first 14 periods
    assert atr.iloc[13] == 4.0
    
    # TR for index 14 is max(13-9, |13-10|, |9-10|) = max(4, 3, 1) = 4.0
    expected_atr_14 = ((13 * 4.0) + 4.0) / 14.0
    np.testing.assert_allclose(atr.iloc[14], expected_atr_14, rtol=1e-9)
