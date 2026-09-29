import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class SignalState(Enum):
    ACCEPTED = "ACCEPTED"
    SUPPRESSED_OPEN_POSITION = "SUPPRESSED_OPEN_POSITION"
    REJECTED_CAPACITY = "REJECTED_CAPACITY"
    REJECTED_CASH = "REJECTED_CASH"
    REJECTED_LIQUIDITY_CAP = "REJECTED_LIQUIDITY_CAP"
    REJECTED_GAP_FILTER = "REJECTED_GAP_FILTER"
    EXPIRED_NO_DATA = "EXPIRED_NO_DATA"
    EXPIRED_INVALID_BAR = "EXPIRED_INVALID_BAR"
    EXPIRED_CIRCUIT_LOCK = "EXPIRED_CIRCUIT_LOCK"

class DataQualityFlag(Enum):
    VALID = "VALID"
    STALE_DATA = "STALE_DATA"
    INVALID_OHLC = "INVALID_OHLC"
    CA_SUSPECT = "CA_SUSPECT"
    MISSING_BAR = "MISSING_BAR"

@dataclass
class Bar:
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float
    split_factor: float = 1.0
    quality_flag: DataQualityFlag = DataQualityFlag.VALID

@dataclass
class Signal:
    signal_id: str
    symbol: str
    signal_date: datetime.date
    status: SignalState
    atr_signal: float
    features: Dict[str, Any]
    
@dataclass
class Position:
    symbol: str
    entry_date: datetime.date
    entry_price: float
    quantity: int
    frozen_atr: float
    stop_loss: float
    target: float
    
class ExitReason(Enum):
    STOP = "STOP"
    TARGET = "TARGET"
    GAP_STOP = "GAP_STOP"
    GAP_TARGET = "GAP_TARGET"
    TIME_STOP = "TIME_STOP"
    CENSORED = "CENSORED"
    DATA_TERMINATION = "DATA_TERMINATION"

@dataclass
class Trade:
    trade_id: str
    signal_id: str
    symbol: str
    entry_date: datetime.date
    exit_date: datetime.date
    entry_price: float
    exit_price: float
    quantity: int
    exit_reason: ExitReason
    gross_pnl: float
    fees: float
    net_pnl: float
    r_frictionless: float
    r_price_mult: float
    r_net: float
    holding_sessions: int
    mfe_r: float
    mae_r: float
    gap_pct: float
