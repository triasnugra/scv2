"""T3 - Pullback Fibonacci 0.75/0.786 searah musim."""
from __future__ import annotations
import numpy as np
from ..indicators import atr, vol_ratio
from ..structure import find_impulse
from .common import arrays, mk


def pullback_fib(closed, side, c):
    out = []
    t = closed[c["trigger_tf"]]
    if len(t) < 30:
        return out
    a = float(atr(t).iloc[-1])
    lo, hi, cl, op, sg = arrays(t, side)
    vol = t["volume"].to_numpy()
    for tf in c["impulse_tfs"]:
        imp = find_impulse(closed[tf], side, c["pivot_k"], c["min_impulse_pct"], c["impulse_back"])
        if not imp:
            continue
        Ht, Lt = (imp["H"], imp["L"]) if side == "long" else (-imp["L"], -imp["H"])
        rg = Ht - Lt
        p75, p786 = Ht - 0.75 * rg, Ht - 0.786 * rg
        tol = abs(p75) * c["zone_tol_pct"] / 100
        rlow = lo[-c["recent_bars"]:].min()
        in_zone = Lt < rlow <= p75 + tol
        stoprun = rlow < p786 and cl[-1] > p786
        reversal = cl[-1] > op[-1] and (cl[-1] > max(op[-2], cl[-2]) or stoprun)
        near = cl[-1] <= p75 + 1.5 * a
        if not near or cl[-1] < Lt:
            continue
        buf = max(c["stop_buf_atr"] * a, abs(p75) * 0.0003)
        stop = (min(rlow, p786) - buf) * sg
        q = ["stop_run_di_zona"] if stoprun else []
        vr = vol_ratio(vol, len(t) - 3, len(t) - 1)
        ok = in_zone and reversal and cl[-1] > p786 and (cl[-1] - p75) <= c["chase_atr"] * a
        out.append(mk("T3", c["trigger_tf"], side, "ACTIVE" if ok else "PENDING", t["close"].iloc[-1], "MARKET",
                      stop, p75 * sg, "FIB_0.75", q, vr, impulse_tf=tf, fib75=p75 * sg, fib786=p786 * sg))
    return out
