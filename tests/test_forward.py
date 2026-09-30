import unittest
import datetime
import os
import sqlite3

from bveqse.forward.state import ForwardState
from bveqse.forward.config_freeze import generate_config_hash
from bveqse.core.types import Signal, SignalState

class TestForwardEngine(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_forward.db"
        try:
            os.remove(self.db_path)
        except:
            pass
        self.state = ForwardState(self.db_path)

    def tearDown(self):
        try:
            os.remove(self.db_path)
            os.remove(self.db_path + "-wal")
            os.remove(self.db_path + "-shm")
        except:
            pass

    def test_idempotency_signal_persistence(self):
        s1 = Signal("sig_1", "RELIANCE.NS", datetime.date(2026, 9, 30), SignalState.ACCEPTED, 10.5, {"ema": 100})
        # Insert once
        self.state.persist_signals([s1])
        
        # Insert again
        self.state.persist_signals([s1])
        
        # Verify only one exists
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM signals")
            count = cur.fetchone()[0]
        
        self.assertEqual(count, 1)

    def test_config_hash_consistency(self):
        h1 = generate_config_hash()
        h2 = generate_config_hash()
        self.assertEqual(h1, h2)

if __name__ == '__main__':
    unittest.main()
