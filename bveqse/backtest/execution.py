import math
from typing import Optional, Tuple
from bveqse.core.types import Bar, Signal, Position, ExitReason, SignalState
from bveqse.config import StrategyConfig, CostConfig

def evaluate_entry(
    signal: Signal, 
    entry_bar: Bar, 
    prev_close: float,
    config: StrategyConfig, 
    cost_config: CostConfig
) -> Tuple[SignalState, Optional[Position], Optional[float]]:
    """
    Evaluates a pending signal against the entry bar (t+1).
    Returns (New SignalState, Position if entered, gap_pct)
    """
    if entry_bar.quality_flag != entry_bar.quality_flag.VALID:
        return SignalState.EXPIRED_INVALID_BAR, None, None
        
    # Check invalid OHLC
    if entry_bar.high < max(entry_bar.open, entry_bar.close, entry_bar.low) or \
       entry_bar.low > min(entry_bar.open, entry_bar.close, entry_bar.high):
        return SignalState.EXPIRED_INVALID_BAR, None, None
        
    # Circuit-lock heuristic (upper circuit)
    if config.circuit_lock_heuristic:
        if (entry_bar.open == entry_bar.high == entry_bar.low == entry_bar.close) and \
           (entry_bar.open > prev_close):
            return SignalState.EXPIRED_CIRCUIT_LOCK, None, None
            
    # Calculate gap
    gap_pct = (entry_bar.open / prev_close) - 1.0
    
    # Fill price
    s_buy = cost_config.slippage_rate
    f_entry = entry_bar.open * (1.0 + s_buy)
    
    # Stop and target
    R = config.stop_atr_multiple_k * signal.atr_signal
    stop_loss = f_entry - R
    target = f_entry + (config.target_r_multiple_m * R)
    
    # Position object (quantity is 0 initially, sized by portfolio)
    pos = Position(
        symbol=signal.symbol,
        entry_date=entry_bar.date,
        entry_price=f_entry,
        quantity=0, # to be set by sizing logic
        frozen_atr=signal.atr_signal,
        stop_loss=stop_loss,
        target=target
    )
    
    return SignalState.ACCEPTED, pos, gap_pct

def evaluate_exit(
    position: Position, 
    bar: Bar, 
    prev_close: float,
    config: StrategyConfig, 
    cost_config: CostConfig,
    is_last_bar: bool = False
) -> Tuple[bool, Optional[float], Optional[ExitReason]]:
    """
    Evaluates an open position against the current day's bar.
    Returns (is_exited, exit_price, exit_reason)
    """
    if is_last_bar:
        # End of data / permanent data termination
        return True, bar.close, ExitReason.CENSORED
        
    s_sell = cost_config.slippage_rate
    S = position.stop_loss
    T = position.target
    
    # Circuit lock heuristics for exits (lower circuit lock deferred)
    if config.circuit_lock_heuristic:
        if (bar.open == bar.high == bar.low == bar.close) and (bar.close < prev_close):
            # Cannot exit on lower circuit lock
            return False, None, None
            
    # 1. Gap through stop
    if bar.open <= S:
        exit_price = bar.open * (1.0 - s_sell) if config.slippage_on_limit_exits else bar.open
        return True, exit_price, ExitReason.GAP_STOP
        
    # 2. Gap through target
    if bar.open >= T:
        exit_price = bar.open * (1.0 - s_sell) if config.slippage_on_limit_exits else bar.open
        return True, exit_price, ExitReason.GAP_TARGET
        
    touched_stop = bar.low <= S
    touched_target = bar.high >= T
    
    # Intrabar ambiguity
    if touched_stop and touched_target:
        if config.intrabar_ambiguity == "STOP_FIRST":
            exit_price = S * (1.0 - s_sell) if config.slippage_on_limit_exits else S
            return True, exit_price, ExitReason.STOP
    
    # 3. Stop touched
    if touched_stop:
        exit_price = S * (1.0 - s_sell) if config.slippage_on_limit_exits else S
        return True, exit_price, ExitReason.STOP
        
    # 4. Target touched
    if touched_target:
        exit_price = T * (1.0 - s_sell) if config.slippage_on_limit_exits else T
        return True, exit_price, ExitReason.TARGET
        
    return False, None, None
