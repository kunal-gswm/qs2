from dataclasses import dataclass, field
import datetime
from typing import Dict, Any

@dataclass(frozen=True)
class CostConfig:
    version_id: str
    effective_date: datetime.date
    verification_date: datetime.date
    
    # Fractional rates (e.g. 0.001 = 0.1%)
    stt_rate: float
    exchange_transaction_charge_rate: float
    sebi_turnover_fee_rate: float
    stamp_duty_rate: float
    gst_rate: float
    
    # Brokerage assumption
    brokerage_rate: float
    brokerage_cap_inr: float
    
    # Flat charges
    dp_charge_per_sell_inr: float
    
    # Slippage (not a fee, but cost of execution)
    slippage_rate: float
    
    # Source metadata
    sources: Dict[str, str]

# Frozen explicitly for BVEQSE v1.0
INDIA_EQUITY_DELIVERY_2026_09 = CostConfig(
    version_id="INDIA_EQUITY_DELIVERY_2026_09",
    effective_date=datetime.date(2026, 9, 1),
    verification_date=datetime.date(2026, 9, 29),
    
    stt_rate=0.001,  # 0.1% both legs
    exchange_transaction_charge_rate=0.0000322,  # NSE cash ~0.00322%
    sebi_turnover_fee_rate=0.000001,  # INR 10 per crore = 0.0001%
    stamp_duty_rate=0.00015,  # 0.015% buy leg only
    gst_rate=0.18,  # 18% on (brokerage + exchange + SEBI)
    
    brokerage_rate=0.0,  # Discount broker delivery assumption
    brokerage_cap_inr=0.0,
    
    dp_charge_per_sell_inr=15.34,  # CDSL/NSDL typical DP charge + GST roughly
    
    slippage_rate=0.0005,  # 0.05% per leg baseline
    
    sources={
        "stt": "Income Tax Department India - Securities Transaction Tax",
        "exchange_transaction_charge": "NSE India Circulars - Cash Market",
        "sebi_turnover_fee": "SEBI Fees Circular",
        "stamp_duty": "Indian Stamp Act (2020 revision)",
        "gst": "GST Council",
        "brokerage": "Discount broker standard (e.g. Zerodha/Upstox delivery)",
        "slippage": "BVEQSE PRD Baseline"
    }
)

@dataclass(frozen=True)
class StrategyConfig:
    strategy_version: str = "BVEQSE_v1.0"
    
    # Baseline Parameters
    ema_period: int = 50
    ema_slope_lag: int = 5
    consolidation_lookback_L: int = 20
    range_threshold_rho: float = 0.10
    
    # Compression rule
    compression_mode: str = "median"
    compression_window_La: int = 20
    
    atr_period_NA: int = 14
    volume_multiple_mu: float = 1.5
    volume_window_Lv: int = 20
    liquidity_floor_inr: float = 100000000.0  # 10 crore
    
    stop_atr_multiple_k: float = 1.5
    target_r_multiple_m: float = 2.0
    
    risk_fraction_f: float = 0.005
    max_positions: int = 10
    max_weight: float = 0.20
    adv_participation_cap: float = 0.02
    
    slippage_on_limit_exits: bool = True
    intrabar_ambiguity: str = "STOP_FIRST"
    circuit_lock_heuristic: bool = True
    
    price_series: str = "split_bonus_adjusted"  # Baseline is not dividend-adjusted
    history_start: datetime.date = datetime.date(2017, 1, 1)
    
    universe_provider: str = "CURRENT_ACTIVE_UNIVERSE"
    universe_point_in_time: bool = False
    
    master_seed: int = 20260929
    n_bootstrap: int = 10000
    n_monte_carlo: int = 10000

BASELINE_CONFIG = StrategyConfig()

def to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, '__dataclass_fields__'):
        return {f.name: to_dict(getattr(obj, f.name)) for f in obj.__dataclass_fields__.values()}
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    else:
        return obj
