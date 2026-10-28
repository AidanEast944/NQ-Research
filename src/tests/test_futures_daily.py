import sys, os, unittest, tempfile
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import futures_daily as fd


def write(d, sym, closes, ids):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="B")
    pd.DataFrame({"date": idx, "open": closes, "high": closes, "low": closes, "close": closes,
                  "volume": 1, "instrument_id": ids}).to_csv(os.path.join(d, f"{sym}.csv"), index=False)


class TestFuturesDaily(unittest.TestCase):
    def test_roll_day_return_is_masked_not_a_fake_move(self):
        d = tempfile.mkdtemp()
        write(d, "ZN", [100, 101, 110, 111], [1, 1, 2, 2])    # 101 -> 110 is a roll gap, not a return
        r = fd.returns(fd.load("ZN", d))
        self.assertAlmostEqual(r.iloc[1], 0.01)
        self.assertEqual(r.iloc[2], 0.0)                        # masked roll day
        self.assertAlmostEqual(r.iloc[3], 1 / 110)

    def test_nonpositive_price_days_are_masked(self):
        idx = pd.to_datetime(["2020-04-17", "2020-04-20", "2020-04-21", "2020-04-22"])
        df = pd.DataFrame({"close": [18.0, -2.67, 10.0, 11.0], "instrument_id": 1}, index=idx)
        r = fd.returns(df, fill_roll_days=False)
        self.assertTrue(r.iloc[1:3].isna().all())
        self.assertAlmostEqual(r.iloc[3], 0.1)

    def test_first_day_is_zero_and_no_nan_when_filled(self):
        d = tempfile.mkdtemp(); write(d, "ZN", [100, 101], [1, 1])
        self.assertFalse(fd.returns(fd.load("ZN", d)).isna().any())

    def test_unfilled_keeps_nan_on_roll(self):
        d = tempfile.mkdtemp(); write(d, "ZN", [100, 110], [1, 2])
        self.assertTrue(np.isnan(fd.returns(fd.load("ZN", d), fill_roll_days=False).iloc[1]))

    def test_load_all_aligns_symbols(self):
        d = tempfile.mkdtemp(); write(d, "A", [1, 2, 3], [1, 1, 1]); write(d, "B", [1, 1, 1], [1, 1, 1])
        out = fd.load_all(["A", "B"], d)
        self.assertEqual(list(out.columns), ["A", "B"]); self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
