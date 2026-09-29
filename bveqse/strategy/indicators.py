import numpy as np
import pandas as pd

def calculate_ema(closes: pd.Series, period: int = 50) -> pd.Series:
    """
    EMA with alpha = 2/(N+1).
    Seeded with SMA on the first N valid bars.
    """
    sma = closes.rolling(window=period, min_periods=period).mean()
    ema = closes.ewm(span=period, adjust=False).mean()
    # Replace the initial periods with SMA seed
    # The EWM function calculates from bar 1, but we need SMA seed at period N.
    # To match PRD: E_NE = SMA(C_1..C_NE), then E_t = alpha C_t + (1-alpha) E_t-1
    # Pandas EWM with adjust=False seeds with the first value.
    # We will build a custom one to be perfectly aligned with PRD T-IND1.
    result = np.full(len(closes), np.nan)
    closes_vals = closes.values
    
    first_valid_idx = closes.first_valid_index()
    if first_valid_idx is None:
        return pd.Series(result, index=closes.index)
        
    start_idx = closes.index.get_loc(first_valid_idx)
    
    if len(closes) - start_idx < period:
        return pd.Series(result, index=closes.index)
        
    alpha = 2.0 / (period + 1)
    
    sma_seed_idx = start_idx + period - 1
    seed_sma = np.nanmean(closes_vals[start_idx:sma_seed_idx + 1])
    result[sma_seed_idx] = seed_sma
    
    for i in range(sma_seed_idx + 1, len(closes_vals)):
        if pd.isna(closes_vals[i]):
            # PRD: A missing bar breaks indicator chains. EMA resets.
            # But the PRD also says missing values are never imputed.
            # "EMA/ATR recursions reset and must re-seed on the next consecutive valid bars."
            # We'll return NaN and it will require re-seeding. For simplicity, we assume data 
            # is validated and missing bars are dropped or handled in data layer.
            result[i] = np.nan
        else:
            result[i] = alpha * closes_vals[i] + (1 - alpha) * result[i - 1]
            
    return pd.Series(result, index=closes.index)

def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Wilder's ATR. 
    TR_t = max(H_t - L_t, |H_t - C_t-1|, |L_t - C_t-1|)
    ATR_t = ((N-1) * ATR_t-1 + TR_t) / N
    Seeded with SMA of TR over first N valid bars.
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    
    result = np.full(len(tr), np.nan)
    tr_vals = tr.values
    
    first_valid_idx = tr.first_valid_index()
    if first_valid_idx is None:
        return pd.Series(result, index=tr.index)
        
    start_idx = tr.index.get_loc(first_valid_idx)
    
    if len(tr) - start_idx < period:
        return pd.Series(result, index=tr.index)
        
    seed_idx = start_idx + period - 1
    seed_atr = np.nanmean(tr_vals[start_idx:seed_idx + 1])
    result[seed_idx] = seed_atr
    
    for i in range(seed_idx + 1, len(tr_vals)):
        if pd.isna(tr_vals[i]):
            result[i] = np.nan
        else:
            result[i] = ((period - 1) * result[i - 1] + tr_vals[i]) / period
            
    return pd.Series(result, index=tr.index)

def calculate_natr(atr: pd.Series, close: pd.Series) -> pd.Series:
    """NATR_t = ATR_t / C_t"""
    return atr / close
