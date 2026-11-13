"""T2 - Breakout -> Retest (flip level). Breakout palsu => dievaluasi sebagai T1 arah sebaliknya."""
from __future__ import annotations
import numpy as np
from ..indicators import vol_ratio
from .common import arrays, mk
from .t1_sweep import sweep_reclaim


def breakout_retest(df, level, side, c, atr_v, tf, t1c=None):
    n = len(df)
    if n < 30 or not np.isfinite(atr_v):
        return None
    lo, hi, cl, op, sg = arrays(df, side)
    vol = df["volume"].to_numpy()
    L = level * sg; aL = abs(L)
    for b in range(n - 1, max(n - 1 - c["lookback_bars"], 1) - 1, -1):
        if not (cl[b] > L and cl[b - 1] <= L):
            continue
        vr = vol_ratio(vol, b, b)
        if vr < c["vol_mult"]:
            continue
        after = cl[b + 1:]
        k = len(after)
        if (after <= L).any():
            if t1c is None:
                return None
            opp = "short" if side == "long" else "long"
            r = sweep_reclaim(df, level, opp, t1c, atr_v, tf, n_max=c["fake_reclaim_bars"], from_t2=True)
            if r:
                r["quality"].append("breakout_palsu")
            return r
        if k > c["max_age_bars"]:
            return None
        buf = max(c["stop_buf_atr"] * atr_v, aL * 0.0003)
        q = ["volume_break"] if vr >= c["vol_mult"] * 1.5 else []
        if k >= 3:
            q.append("konsolidasi_3+")
        touched = lo[-1] <= L + aL * c["retest_tol_pct"] / 100 and cl[-1] > L
        if k >= c["min_consol"] and touched:
            return mk("T2", tf, side, "ACTIVE", cl[-1] * sg, "MARKET", (min(L, lo[-1]) - buf) * sg, level, "flip", q, vr, bars_after=k)
        stop = (min(L, lo[b + 1:].min() if k else L) - buf) * sg
        return mk("T2", tf, side, "PENDING", level, "LIMIT", stop, level, "flip", q, vr, bars_after=k)
    return None
