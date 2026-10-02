import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_performance import summarize, validate_trade


class PerformanceImportTests(unittest.TestCase):
    def test_summary(self):
        trades = [
            validate_trade({"symbol": "A", "entry_date": "2026-01-01", "exit_date": "2026-01-02", "realized_pnl": 20, "planned_rr": 2, "realized_rr": 1}),
            validate_trade({"symbol": "B", "entry_date": "2026-01-03", "exit_date": "2026-01-04", "realized_pnl": -10, "planned_rr": 2, "realized_rr": -1}),
        ]
        summary = summarize(trades)
        self.assertEqual(summary["trade_count"], 2)
        self.assertEqual(summary["win_rate"], 0.5)
        self.assertEqual(summary["profit_factor"], 2.0)
        self.assertEqual(summary["net_pnl"], 10.0)

    def test_rejects_private_broker_fields(self):
        with self.assertRaises(ValueError):
            validate_trade({
                "symbol": "NVDA", "entry_date": "2026-01-01", "exit_date": "2026-01-02",
                "realized_pnl": 1, "account_id": "secret",
            })


if __name__ == "__main__":
    unittest.main()
