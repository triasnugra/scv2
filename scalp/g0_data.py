"""Gate 0 - kualitas data & kelayakan eksekusi."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .util import TF_DELTA, TFS


def check(symbol: str, closed: dict, cfg: dict, now: pd.Timestamp, is_major: bool) -> dict:
    c = cfg["g0"]; reasons = []
    for tf in TFS:
        df = closed.get(tf)
        if df is None or len(df) < c["min_bars"][tf]:
            reasons.append(f"data {tf} kurang ({0 if df is None else len(df)} bar)")
            continue
        d = TF_DELTA[tf]
        exp_open = (now - d).floor(d)
        lag = (exp_open - df.index[-1]) / d
        if lag > c["max_stale_bars"]:
            reasons.append(f"data {tf} basi ({lag:.0f} bar tertinggal)")
        if tf != "1D":
            idx = df.index[-c["gap_check_bars"]:]
            gaps = int((np.diff(idx.values) > np.timedelta64(int(d.total_seconds()), "s")).sum())
            if gaps > c["max_gaps_recent"]:
                reasons.append(f"ada {gaps} gap pada {tf}")
        z = float((df["volume"].iloc[-50:] <= 0).mean())
        if z > c["max_zero_vol_frac"]:
            reasons.append(f"volume nol tidak wajar di {tf} ({z:.0%})")
    if reasons:
        return {"status": "FAIL", "reasons": reasons}
    h1 = closed["1H"].iloc[-24:]
    qv = float((h1["close"] * h1["volume"]).sum())
    if qv < c["min_quote_vol_24h"]:
        reasons.append(f"likuiditas 24j {qv/1e6:.1f}M < {c['min_quote_vol_24h']/1e6:.0f}M USDT")
    if not is_major:
        swing = (h1["high"].max() / h1["low"].min() - 1) * 100
        if swing >= c["scam_pump_pct"]:
            reasons.append(f"pump/dump terisolasi {swing:.0f}% dalam 24j (hindari)")
    return {"status": "FAIL" if reasons else "PASS", "reasons": reasons}
