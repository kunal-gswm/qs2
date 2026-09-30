import sqlite3
import json
import datetime
import hashlib
from typing import List, Dict, Any, Optional

from bveqse.core.types import Signal, SignalState, Trade, Position, ExitReason
from bveqse.config import StrategyConfig, CostConfig

class ForwardState:
    def __init__(self, db_path: str = "bveqse_forward.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            
            conn.execute('''CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY, symbol TEXT, signal_date TEXT,
                status TEXT, atr_signal REAL, features_json TEXT
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY, signal_id TEXT, symbol TEXT,
                entry_date TEXT, exit_date TEXT, entry_price REAL, exit_price REAL,
                quantity INTEGER, exit_reason TEXT, gross_pnl REAL, costs REAL,
                net_pnl REAL, r_net REAL, position_size REAL,
                equity_before REAL, equity_after REAL
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS open_positions (
                symbol TEXT PRIMARY KEY, entry_date TEXT, entry_price REAL,
                quantity INTEGER, frozen_atr REAL, stop_loss REAL, target REAL
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS rejected_signals (
                signal_id TEXT PRIMARY KEY, symbol TEXT, signal_date TEXT,
                rejection_reason TEXT, features_json TEXT
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS manifest (
                key TEXT PRIMARY KEY, value TEXT
            )''')
            
            conn.execute('''CREATE TABLE IF NOT EXISTS run_log (
                run_id TEXT PRIMARY KEY, session_date TEXT, timestamp TEXT,
                status TEXT, flags_json TEXT
            )''')

    def save_manifest(self, data: Dict[str, str]):
        with sqlite3.connect(self.db_path) as conn:
            for k, v in data.items():
                conn.execute("INSERT OR REPLACE INTO manifest (key, value) VALUES (?, ?)", (k, v))

    def get_manifest(self) -> Dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT key, value FROM manifest")
            return {row[0]: row[1] for row in cur.fetchall()}

    def persist_run(self, run_id: str, session_date: datetime.date, status: str, flags: List[str]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_log (run_id, session_date, timestamp, status, flags_json) VALUES (?, ?, ?, ?, ?)",
                (run_id, session_date.isoformat(), datetime.datetime.now(datetime.timezone.utc).isoformat(), status, json.dumps(flags))
            )

    def persist_signals(self, signals: List[Signal]):
        with sqlite3.connect(self.db_path) as conn:
            for s in signals:
                if s.status == SignalState.ACCEPTED:
                    conn.execute(
                        "INSERT OR IGNORE INTO signals VALUES (?, ?, ?, ?, ?, ?)",
                        (s.signal_id, s.symbol, s.signal_date.isoformat(), s.status.value, s.atr_signal, json.dumps(s.features))
                    )
                else:
                    conn.execute(
                        "INSERT OR IGNORE INTO rejected_signals VALUES (?, ?, ?, ?, ?)",
                        (s.signal_id, s.symbol, s.signal_date.isoformat(), s.status.value, json.dumps(s.features))
                    )

    def persist_trades(self, trades: List[Trade]):
        with sqlite3.connect(self.db_path) as conn:
            for t in trades:
                conn.execute(
                    "INSERT OR IGNORE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (t.trade_id, t.signal_id, t.symbol, t.entry_date.isoformat(), t.exit_date.isoformat(),
                     t.entry_price, t.exit_price, t.quantity, t.exit_reason.value, t.gross_pnl, t.fees,
                     t.net_pnl, t.r_net, t.entry_price * t.quantity, 0.0, 0.0) # Equity calculations deferred or tracked separately
                )

    def update_open_positions(self, positions: Dict[str, Position]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM open_positions")
            for p in positions.values():
                conn.execute(
                    "INSERT INTO open_positions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (p.symbol, p.entry_date.isoformat(), p.entry_price, p.quantity, p.frozen_atr, p.stop_loss, p.target)
                )

    def load_open_positions(self) -> Dict[str, Position]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT * FROM open_positions")
            positions = {}
            for row in cur.fetchall():
                positions[row[0]] = Position(
                    row[0], datetime.date.fromisoformat(row[1]), row[2], row[3], row[4], row[5], row[6]
                )
            return positions

    def get_all_trades(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM trades")
            return [dict(row) for row in cur.fetchall()]
