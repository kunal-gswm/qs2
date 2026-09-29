# CURRENT_ACTIVE_UNIVERSE (Intended)
# Due to API constraints, this run uses a capped version.
UNIVERSE_STATUS = "PARTIAL_UNIVERSE"

SYMBOL_MAP = {
    "HUL.NS": "HINDUNILVR.NS",
    "TATAMOTORS.NS": "TATAMOTORS.NS" # Kept for testing failure logs, but handled by skipping if it fails.
}

NIFTY_100 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "HINDUNILVR.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
    "ITC.NS", "ASIANPAINT.NS", "AXISBANK.NS", "LT.NS", "MARUTI.NS"
]
# Deliberately capped to 15 liquid symbols for the ENGINEERING_TEST to avoid timeout
# during the 243-grid Walk-Forward evaluation.
