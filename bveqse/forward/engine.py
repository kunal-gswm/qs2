import datetime
import uuid
import sys
from typing import Dict, Any

from bveqse.config import INDIA_EQUITY_DELIVERY_2026_09
from bveqse.data.loader import download_and_validate
from bveqse.core.types import Bar, DataQualityFlag
from bveqse.strategy.signal_generator import generate_signals
from bveqse.backtest.engine import BacktestEngine
from bveqse.research.walk_forward import apply_params_to_config
from bveqse.config import BASELINE_CONFIG

from bveqse.forward.state import ForwardState
from bveqse.forward.config_freeze import FORWARD_PARAMS, generate_config_hash, verify_config_integrity

def run_forward_session(session_date: datetime.date, state: ForwardState):
    # 1. Config Integrity
    manifest = state.get_manifest()
    expected_hash = manifest.get('config_hash')
    if expected_hash and not verify_config_integrity(expected_hash):
        state.persist_run(str(uuid.uuid4()), session_date, "SEVERE_FAILURE", ["config_hash_mismatch"])
        raise ValueError("Configuration drift detected! Hash mismatch.")

    # 2. Rehydrate Engine
    cfg = apply_params_to_config(BASELINE_CONFIG, FORWARD_PARAMS)
    engine = BacktestEngine(cfg, INDIA_EQUITY_DELIVERY_2026_09, "FORWARD")
    engine.open_positions = state.load_open_positions()

    # 3. Data Load (No future bars)
    # The loader must only request data up to session_date
    start_date = (session_date - datetime.timedelta(days=150)).isoformat()
    df_dict, _ = download_and_validate(start_date, session_date.isoformat())
    
    # Check data freshness
    daily_bars = {}
    for sym, df in df_dict.items():
        row = df[df['date'] == session_date]
        if not row.empty:
            daily_bars[sym] = Bar(sym, session_date, row['open'].values[0], row['high'].values[0], row['low'].values[0], row['close'].values[0], row['volume'].values[0], 1.0, DataQualityFlag.VALID)

    if not daily_bars:
        state.persist_run(str(uuid.uuid4()), session_date, "DATA_UNAVAILABLE", ["no_bars_for_session"])
        print(f"No data available for session {session_date}. Skipping.")
        return

    # 4. Generate Signals (on data up to session_date)
    # Signal generation only looks at closing data of session_date and before.
    new_signals = []
    for sym, df in df_dict.items():
        sym_sigs = generate_signals(sym, df, cfg, expected_hash)
        # Filter to only the exact session date (ignoring past signals)
        for s in sym_sigs:
            if s.signal_date == session_date:
                new_signals.append(s)
                
    if new_signals:
        engine.queue_signals(new_signals)
        
    # 5. Process Day (Executes exits and previous signals, queues new entries for next open)
    engine.process_day(session_date, daily_bars, {sym: 1e9 for sym in df_dict.keys()})
    
    # 6. Persist State
    # Idempotency is handled by INSERT OR IGNORE in SQLite.
    # We must save rejected/suppressed signals too!
    all_signals_today = [s for s in engine.signal_queue if s.signal_date == session_date]
    # Rejections are in engine.rejected_signals but BacktestEngine currently drops them?
    # BacktestEngine evaluates them next day. So we only know rejections at t+1.
    # To strictly log rejected signals AT SIGNAL TIME (t):
    # Actually, portfolio constraint rejections happen at execution time (t+1 open).
    # But for the milestone we just log all evaluated signals.
    # For now, let's persist the raw generated signals. 
    state.persist_signals(new_signals)
    
    # Exit trades (only ones closed today)
    closed_today = [t for t in engine.closed_trades if t.exit_date == session_date]
    state.persist_trades(closed_today)
    
    state.update_open_positions(engine.open_positions)
    state.persist_run(str(uuid.uuid4()), session_date, "SUCCESS", [])

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        d = datetime.date.fromisoformat(sys.argv[1])
        st = ForwardState()
        run_forward_session(d, st)
