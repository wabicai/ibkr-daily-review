import json
import math
import unittest

import pandas as pd

from scripts.build_cache import _complete_history


class CacheIntegrityTests(unittest.TestCase):
    def test_incomplete_daily_bar_is_dropped(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, float("nan")],
                "Volume": [1000, 1200],
            },
            index=pd.to_datetime(["2026-09-30", "2026-10-01"]),
        )
        clean = _complete_history(frame)
        self.assertEqual(clean.index.strftime("%Y-%m-%d").tolist(), ["2026-09-30"])

    def test_non_finite_bar_is_dropped(self):
        frame = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, math.inf],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1200],
            }
        )
        clean = _complete_history(frame)
        self.assertEqual(len(clean), 1)

    def test_strict_json_rejects_nan(self):
        with self.assertRaises(ValueError):
            json.dumps({"price": float("nan")}, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
