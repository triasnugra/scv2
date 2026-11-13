from __future__ import annotations
import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=max(2, n // 2)).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def obv(df: pd.DataFrame) -> pd.Series:
    sign = np.sign(df["close"].diff().fillna(0))
    return (sign * df["volume"]).cumsum()


def vol_ratio(vol: np.ndarray, idx_from: int, idx_to: int, base: int = 20) -> float:
    """Volume maksimum pada [idx_from, idx_to] dibanding rata-rata `base` bar sebelum idx_from."""
    if idx_from < 5:
        return 0.0
    ref = vol[max(0, idx_from - base):idx_from]
    m = float(np.mean(ref)) if len(ref) else 0.0
    if m <= 0:
        return 0.0
    return float(np.max(vol[idx_from:idx_to + 1])) / m
