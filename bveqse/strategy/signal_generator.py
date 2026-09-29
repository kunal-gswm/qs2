import pandas as pd
import numpy as np
from typing import List
import hashlib
from bveqse.core.types import Signal, SignalState, DataQualityFlag
from bveqse.config import StrategyConfig
from bveqse.strategy.indicators import calculate_ema, calculate_atr, calculate_natr

def generate_signals(
    symbol: str, 
    df: pd.DataFrame, 
    config: StrategyConfig, 
    config_hash: str
) -> List[Signal]:
    """
    Canonical signal generator for BVEQSE.
    Expects df with columns: ['date', 'open', 'high', 'low', 'close', 'volume', 'quality_flag']
    Sorted by date chronologically.
    """
    if len(df) == 0:
        return []
        
    df = df.copy()
    
    # 1. Calculate indicators
    df['ema'] = calculate_ema(df['close'], config.ema_period)
    df['ema_lag'] = df['ema'].shift(config.ema_slope_lag)
    df['atr'] = calculate_atr(df['high'], df['low'], df['close'], config.atr_period_NA)
    df['natr'] = calculate_natr(df['atr'], df['close'])
    
    # 2. Prior window extremes (L)
    L = config.consolidation_lookback_L
    # strictly backward-looking past window (t-L to t-1)
    df['hh_prev'] = df['high'].shift(1).rolling(L).max()
    df['ll_prev'] = df['low'].shift(1).rolling(L).min()
    df['range_prev'] = (df['hh_prev'] - df['ll_prev']) / df['ll_prev']
    
    # 3. Compression (NATR)
    La = config.compression_window_La
    # median {NATR_{t-1-La} ... NATR_{t-2}}
    df['natr_lag2'] = df['natr'].shift(2)
    if config.compression_mode == "median":
        df['natr_median_ref'] = df['natr_lag2'].rolling(La).median()
    elif config.compression_mode == "off":
        df['natr_median_ref'] = np.inf
    elif config.compression_mode == "25th percentile":
        df['natr_median_ref'] = df['natr_lag2'].rolling(La).quantile(0.25)
    else:
        df['natr_median_ref'] = df['natr_lag2'].rolling(La).median()
        
    df['natr_prev'] = df['natr'].shift(1)
    
    # 4. Volume
    Lv = config.volume_window_Lv
    # V_{Lv, t-1} is simple mean of prior completed sessions
    df['vol_prev_avg'] = df['volume'].shift(1).rolling(Lv).mean()
    
    # 5. Liquidity (Traded value median t-60 to t-1)
    df['traded_value'] = df['close'] * df['volume']
    df['traded_value_median_60'] = df['traded_value'].shift(1).rolling(60).median()
    
    signals = []
    
    # Warm-up requirement calculation
    # W(theta) = max(N_E + 5, N_A + L_a + 2, L + 1, L_v + 1, 62)
    # The config defines max parameters. 
    W = max(config.ema_period + config.ema_slope_lag, 
            config.atr_period_NA + config.compression_window_La + 2,
            config.consolidation_lookback_L + 1,
            config.volume_window_Lv + 1,
            62)
            
    for i in range(len(df)):
        if i < W - 1:
            continue
            
        row = df.iloc[i]
        
        # C8: Bar valid
        if row['quality_flag'] != DataQualityFlag.VALID:
            continue
            
        # C1: Ct > Et
        c1 = row['close'] > row['ema']
        # C2: Et > Et-5
        c2 = row['ema'] > row['ema_lag']
        # C3: Range <= rho
        c3 = row['range_prev'] <= config.range_threshold_rho
        # C4: Compression
        c4 = row['natr_prev'] < row['natr_median_ref'] if config.compression_mode != "off" else True
        # C5: Breakout
        c5 = row['close'] > row['hh_prev']
        # C6: Volume
        c6 = (row['volume'] > config.volume_multiple_mu * row['vol_prev_avg']) and (row['volume'] > 0)
        # C7: Liquidity
        c7 = row['traded_value_median_60'] >= config.liquidity_floor_inr
        
        if c1 and c2 and c3 and c4 and c5 and c6 and c7:
            # Generate ID
            # signal_id = SHA-256 (strategy version || symbol || signal date || config hash)
            sig_str = f"{config.strategy_version}|{symbol}|{row['date'].isoformat()}|{config_hash}"
            sig_id = hashlib.sha256(sig_str.encode('utf-8')).hexdigest()[:16]
            
            features = {
                "ema": float(row['ema']),
                "ema_lag": float(row['ema_lag']),
                "atr": float(row['atr']),
                "natr": float(row['natr']),
                "natr_prev": float(row['natr_prev']),
                "natr_median_ref": float(row['natr_median_ref']),
                "hh_prev": float(row['hh_prev']),
                "range_prev": float(row['range_prev']),
                "volume": float(row['volume']),
                "vol_prev_avg": float(row['vol_prev_avg']),
                "traded_value_median_60": float(row['traded_value_median_60'])
            }
            
            # Initial state ACCEPTED; capacity/portfolio module may reject it later
            signal = Signal(
                signal_id=sig_id,
                symbol=symbol,
                signal_date=row['date'],
                status=SignalState.ACCEPTED,
                atr_signal=float(row['atr']),
                features=features
            )
            signals.append(signal)
            
    return signals
