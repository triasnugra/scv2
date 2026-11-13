"""Simulator paper-trade (dipakai live journal & backtest). Konservatif: stop dicek lebih dulu dalam satu bar."""
from __future__ import annotations
import pandas as pd


def simulate(sig: dict, bars: pd.DataFrame, cfg: dict) -> dict:
    """bars = candle 5m TERTUTUP dengan open_time >= waktu sinyal."""
    s = cfg["sim"]; sg = 1 if sig["side"] == "long" else -1
    n = len(bars); idx = bars.index
    if n == 0:
        return {"status": "PENDING"}
    o, h, l, c = (bars[k].to_numpy() for k in ("open", "high", "low", "close"))
    e, stop, tp1, tp2 = sig["entry"], sig["stop"], sig["tp1"], sig.get("tp2")
    f = cfg["g7"]["tp1_fraction"]
    risk_unit = sig["stop_pct"] + sig["cost_pct"]
    fill = None
    if sig["entry_type"] == "MARKET":
        fill, fp = 0, o[0]
    else:
        for i in range(min(n, s["entry_expiry_bars"])):
            if (l[i] <= e) if sg == 1 else (h[i] >= e):
                fill, fp = i, e
                break
            if (h[i] >= tp1) if sg == 1 else (l[i] <= tp1):
                return {"status": "CANCELLED", "outcome": "TP1_SEBELUM_FILL", "exit_ts": str(idx[i])}
        if fill is None:
            if n >= s["entry_expiry_bars"]:
                return {"status": "EXPIRED", "outcome": "LIMIT_TIDAK_TERISI", "exit_ts": str(idx[s["entry_expiry_bars"] - 1])}
            return {"status": "PENDING"}
    stage, cur_stop, pct1 = 0, stop, 0.0
    pc = lambda p: sg * (p - fp) / fp * 100

    def done(k, outcome, gross):
        r = (gross - (risk_unit - sig["stop_pct"])) / risk_unit
        return {"status": "CLOSED", "outcome": outcome, "fill_ts": str(idx[fill]), "exit_ts": str(idx[k]),
                "r": round(r, 3), "bars_held": int(k - fill + 1)}

    for k in range(fill, n):
        hit_stop = (l[k] <= cur_stop) if sg == 1 else (h[k] >= cur_stop)
        if stage == 0:
            hit_tp = ((h[k] >= tp1) if sg == 1 else (l[k] <= tp1)) and (k > fill or sig["entry_type"] == "MARKET")
            if hit_stop:
                return done(k, "SL", pc(cur_stop))
            if hit_tp:
                stage, pct1, cur_stop = 1, pc(tp1), fp
                continue
            if k - fill + 1 >= s["time_stop_bars"]:
                return done(k, "TIME", pc(c[k]))
        else:
            if hit_stop:
                return done(k, "TP1_BE", f * pct1)
            if tp2 is not None and ((h[k] >= tp2) if sg == 1 else (l[k] <= tp2)):
                return done(k, "TP2", f * pct1 + (1 - f) * pc(tp2))
            if k - fill + 1 >= s["max_hold_bars"]:
                return done(k, "TIME2", f * pct1 + (1 - f) * pc(c[k]))
    return {"status": "OPEN", "fill_ts": str(idx[fill]), "stage": stage}
