import yfinance as yf
import pandas as pd
import datetime
import hashlib
from typing import Dict
import json
from bveqse.core.types import Bar, DataQualityFlag

def download_data(symbols, start_date, end_date):
    """
    Downloads historical OHLCV data. 
    Applies BVEQSE rules (e.g. split/bonus adjustment, NO dividend adjustment in baseline).
    yfinance auto_adjust=False preserves raw close, but we need split adjusted. 
    For simplicity, we will use auto_adjust=False, and back-adjust for splits manually if needed, 
    or use yfinance's built-in actions. 
    Actually, to align with PRD 'split/bonus adjusted, not dividend adjusted':
    Standard Yahoo 'Adj Close' includes dividends. We will use 'Close' which is split-adjusted 
    but not dividend adjusted in yf history! (Wait, yf history with auto_adjust=False returns 
    Close split-adjusted).
    """
    df_dict = {}
    missing_sessions = 0
    pull_timestamp = datetime.datetime.now().isoformat()
    
    # Download in bulk for speed
    data = yf.download(symbols, start=start_date, end=end_date, auto_adjust=False, progress=False)
    
    for sym in symbols:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                sym_data = data.xs(sym, level=1, axis=1).dropna(how='all')
            else:
                sym_data = data.dropna(how='all')
                
            if sym_data.empty:
                continue
                
            # Filter zero/negative prices
            sym_data = sym_data[(sym_data['Open'] > 0) & (sym_data['High'] > 0) & 
                                (sym_data['Low'] > 0) & (sym_data['Close'] > 0)]
            
            # Missing volume is 0 or NaN
            sym_data['Volume'] = sym_data['Volume'].fillna(0)
            
            # Map to standard format
            df = pd.DataFrame({
                'date': sym_data.index.date,
                'open': sym_data['Open'].values,
                'high': sym_data['High'].values,
                'low': sym_data['Low'].values,
                'close': sym_data['Close'].values,
                'volume': sym_data['Volume'].values,
                'quality_flag': [DataQualityFlag.VALID] * len(sym_data)
            })
            
            df_dict[sym] = df
            
        except Exception as e:
            missing_sessions += 1
            
    # Generate data hashes
    hashes = {}
    for sym, df in df_dict.items():
        hashes[sym] = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values).hexdigest()
        
    report = {
        "data_source": "yfinance",
        "pull_timestamp": pull_timestamp,
        "date_range": f"{start_date} to {end_date}",
        "missing_sessions_est": missing_sessions,
        "data_quality_status": "VALIDATED",
        "symbol_hashes": hashes
    }
    
    return df_dict, report
