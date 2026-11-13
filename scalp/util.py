"""Utilitas waktu & candle tertutup (anti look-ahead)."""
from __future__ import annotations
import pandas as pd

TFS = ["5m", "15m", "1H", "4H", "1D"]
TF_DELTA = {
    "5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15),
    "1H": pd.Timedelta(hours=1), "4H": pd.Timedelta(hours=4), "1D": pd.Timedelta(days=1),
}
# batas jumlah candle yang dilihat engine (sama untuk live & backtest agar hasil identik)
CAPS = {"5m": 300, "15m": 300, "1H": 400, "4H": 250, "1D": 200}


def to_utc(ts) -> pd.Timestamp:
    t = pd.Timestamp(ts)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def snap(now) -> pd.Timestamp:
    """Waktu analisis = penutupan candle 5m terakhir."""
    return to_utc(now).floor("5min")


def closed_view(df: pd.DataFrame, tf: str, now) -> pd.DataFrame:
    """Hanya candle yang SUDAH tertutup pada waktu `now`."""
    if df is None or len(df) == 0:
        return df
    cut = to_utc(now) - TF_DELTA[tf]
    n = df.index.searchsorted(cut, side="right")
    return df.iloc[:n]


def prepare(frames: dict, now) -> dict:
    out = {}
    for tf in TFS:
        df = frames.get(tf)
        if df is None:
            continue
        v = closed_view(df, tf, now)
        out[tf] = v.iloc[-CAPS[tf]:]
    return out


def pct(a: float, b: float) -> float:
    return (a - b) / b * 100.0


def cost_pct(cfg: dict) -> float:
    c = cfg["costs"]
    return 2 * (c["fee_pct"] + c["slippage_pct"]) + c["spread_pct"]
