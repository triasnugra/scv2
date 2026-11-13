"""Fixture sintetis multi-TF dari deret 5m (konsisten antar-TF)."""
import numpy as np
import pandas as pd

AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
RULE = {"15m": "15min", "1H": "1h", "4H": "4h", "1D": "1D"}


def make_5m(prices: np.ndarray, start="2026-03-02 00:00", vol=None, wick=0.0006, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=len(prices), freq="5min", tz="UTC")
    c = prices.astype(float)
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) * (1 + rng.uniform(0, wick, len(c)))
    lo = np.minimum(o, c) * (1 - rng.uniform(0, wick, len(c)))
    v = np.full(len(c), 1e6) * rng.uniform(0.8, 1.2, len(c)) if vol is None else vol
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": v}, index=idx)


def frames_from_5m(df5: pd.DataFrame) -> dict:
    f = {"5m": df5}
    for tf, r in RULE.items():
        f[tf] = df5.resample(r, label="left", closed="left").agg(AGG).dropna()
    return f


def range_prices(n, lo=100.0, hi=104.0, period=192, seed=2):
    """Osilasi sinus antara lo-hi (period dalam bar 5m) + noise kecil."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    mid, amp = (lo + hi) / 2, (hi - lo) / 2
    return mid + amp * np.sin(2 * np.pi * t / period) + rng.normal(0, 0.05, n)


def trend_prices(n, start=100.0, drift=0.0004, seed=3):
    rng = np.random.default_rng(seed)
    return start * np.exp(np.cumsum(rng.normal(drift, 0.0015, n)))
