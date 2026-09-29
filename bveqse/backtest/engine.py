import pandas as pd
from typing import List, Dict, Tuple
from bveqse.core.types import Bar, Signal, Position, Trade, ExitReason, SignalState
from bveqse.config import StrategyConfig, CostConfig
from bveqse.backtest.execution import evaluate_entry, evaluate_exit
from bveqse.backtest.costs import calculate_leg_costs
from bveqse.backtest.sizing import calculate_position_size
from bveqse.strategy.signal_generator import generate_signals

class BacktestEngine:
    def __init__(self, config: StrategyConfig, cost_config: CostConfig, config_hash: str):
        self.config = config
        self.cost_config = cost_config
        self.config_hash = config_hash
        
        self.cash = 1000000.0  # Default initial capital
        self.equity = self.cash
        
        self.open_positions: Dict[str, Position] = {}
        self.pending_signals: List[Signal] = []
        self.closed_trades: List[Trade] = []
        self.signals_record: List[Signal] = []
        
        # We need a unified timeline for the event loop
        # For simplicity, we assume we process day-by-day across all symbols
        
    def _execute_exit(self, position: Position, exit_price: float, exit_reason: ExitReason, exit_date) -> Trade:
        costs = calculate_leg_costs(exit_price, position.quantity, False, self.cost_config)
        self.cash += (exit_price * position.quantity) - costs
        
        # Calculate P&L metrics
        gross_pnl = (exit_price - position.entry_price) * position.quantity
        
        # Need entry costs again to compute net accurately (though they were paid)
        entry_costs = calculate_leg_costs(position.entry_price, position.quantity, True, self.cost_config)
        total_fees = entry_costs + costs
        net_pnl = gross_pnl - total_fees
        
        r_mult = position.frozen_atr * self.config.stop_atr_multiple_k
        r_frict = ((exit_price - position.entry_price) / r_mult) if r_mult > 0 else 0
        r_net = net_pnl / (position.quantity * r_mult) if (position.quantity * r_mult) > 0 else 0
        
        trade = Trade(
            trade_id=f"{position.symbol}_{position.entry_date.isoformat()}_{exit_date.isoformat()}",
            signal_id="derived", # should map to actual signal id
            symbol=position.symbol,
            entry_date=position.entry_date,
            exit_date=exit_date,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            fees=total_fees,
            net_pnl=net_pnl,
            r_frictionless=r_frict,
            r_price_mult=r_frict, # Simplified
            r_net=r_net,
            holding_sessions=0, # Simplified
            mfe_r=0.0,
            mae_r=0.0,
            gap_pct=0.0
        )
        self.closed_trades.append(trade)
        return trade
        
    def process_day(self, date, daily_bars: Dict[str, Bar], median_volume_data: Dict[str, float]):
        """
        Executes PRD Section 7.3 Daily event-loop order.
        """
        # 1. Snapshot Equity
        # eq_d_1 is self.equity from end of yesterday
        snapshot_eq = self.equity
        
        # 2. Open-gap exits
        # (Combined with 4 in a standard bar loop for simplicity of this skeletal implementation,
        # but formally evaluate_exit handles gap logic)
        
        exited_symbols = set()
        for sym, pos in list(self.open_positions.items()):
            if sym in daily_bars:
                bar = daily_bars[sym]
                is_exited, exit_price, reason = evaluate_exit(
                    pos, bar, pos.entry_price, self.config, self.cost_config
                ) # Simplified prev_close usage
                
                if is_exited:
                    self._execute_exit(pos, exit_price, reason, bar.date)
                    del self.open_positions[sym]
                    exited_symbols.add(sym)
                    
        # 3. Pending Entries
        # Sort pending signals by capacity ranking P19
        new_positions_today = 0
        for sig in self.pending_signals:
            if sig.symbol in self.open_positions or sig.symbol in exited_symbols:
                sig.status = SignalState.SUPPRESSED_OPEN_POSITION
                continue
                
            if len(self.open_positions) >= self.config.max_positions:
                sig.status = SignalState.REJECTED_CAPACITY
                continue
                
            if sig.symbol in daily_bars:
                bar = daily_bars[sig.symbol]
                
                # Check eval
                state, pos, gap_pct = evaluate_entry(
                    sig, bar, bar.open, self.config, self.cost_config
                )
                
                sig.status = state
                if state == SignalState.ACCEPTED and pos is not None:
                    # Sizing
                    q = calculate_position_size(
                        snapshot_eq, 
                        self.cash, 
                        pos.entry_price, 
                        self.config.stop_atr_multiple_k * pos.frozen_atr,
                        median_volume_data.get(sig.symbol, 0.0),
                        self.config
                    )
                    
                    if q < 1:
                        sig.status = SignalState.REJECTED_CASH
                        continue
                        
                    pos.quantity = q
                    costs = calculate_leg_costs(pos.entry_price, pos.quantity, True, self.cost_config)
                    total_entry = (pos.entry_price * pos.quantity) + costs
                    
                    if total_entry > self.cash:
                        sig.status = SignalState.REJECTED_CASH
                        continue
                        
                    self.cash -= total_entry
                    self.open_positions[sig.symbol] = pos
                    
        self.pending_signals = []
        
        # 4. Intraday exits (Already processed in step 2 loop using OHLC)
        
        # 5. Mark to market
        market_value = 0.0
        for sym, pos in self.open_positions.items():
            if sym in daily_bars:
                market_value += pos.quantity * daily_bars[sym].close
            else:
                market_value += pos.quantity * pos.entry_price # Stale mark
                
        self.equity = self.cash + market_value
        
        # 6. Signal generation at close is handled by external vectorized pass
        # then injected here for t+1
        
    def queue_signals(self, signals: List[Signal]):
        self.pending_signals.extend(signals)
        self.signals_record.extend(signals)
