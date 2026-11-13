"""T1 - Deviation + Reclaim (liquidity sweep). Trigger utama."""
from __future__ import annotations
import numpy as np
from ..indicators import vol_ratio
from .common import arrays, mk


def sweep_reclaim(df, level, side, c, atr_v, tf, n_max=None, from_t2=False):
    n = len(df)
    if n < 30 or not np.isfinite(atr_v):
        return None
    lo, hi, cl, op, sg = arrays(df, side)
    vol = df["volume"].to_numpy()
    L = level * sg; aL = abs(L)
    nmax = n_max or c["reclaim_bars"]
    min_d, max_d = aL * c["sweep_min_pct"] / 100, aL * c["sweep_max_pct"] / 100
    for s in range(n - 1, max(n - 1 - c["lookback_bars"], 1) - 1, -1):
        if lo[s] > L - min_d or cl[s - 1] < L:
            continue
        r = next((j for j in range(s, min(s + nmax, n)) if cl[j] > L), None)
        end = n if r is None else r + 1
        if L - lo[s:end].min() > max_d:
            continue
        ext = lo[s:].min()
        buf = max(c["stop_buf_atr"] * atr_v, aL * 0.0003)
        stop = (ext - buf) * sg
        if r is None:
            status = "PENDING" if n - s <= nmax else "FAILED"
            age = 0
        elif (cl[r + 1:] <= L).any():
            status, age = "FAILED", 0
        else:
            age = n - 1 - r
            if age > c["max_age_bars"]:
                return None
            status = "ACTIVE" if (cl[-1] - L) <= c["chase_atr"] * atr_v else "PENDING"
        rng_s = hi[s] - lo[s]
        q = []
        if r == s:
            q.append("reclaim_cepat")
        if rng_s > 0 and (min(op[s], cl[s]) - lo[s]) >= c["wick_frac"] * rng_s and cl[s] >= lo[s] + 0.5 * rng_s:
            q.append("absorpsi_wick")
        a0 = max(0, s - 48)
        if sum(1 for j in range(a0, max(a0, s - 1)) if lo[j] < L - aL * 0.0003 and cl[j] >= L) >= 1:
            q.append("deviasi_ganda")
        vr = vol_ratio(vol, s, (r if r is not None else n - 1))
        return mk("T1", tf, side, status, level, "LIMIT", stop, level, "sweep", q, vr,
                  sweep_bar=int(s), age=int(age), from_t2_fail=from_t2)
    return None
