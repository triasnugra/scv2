"""T4 - Reclaim trendline / flip EMA searah musim."""
from __future__ import annotations
import numpy as np
from ..indicators import atr, ema, vol_ratio
from ..structure import pivots
from .common import arrays, mk


def flip_retest(df, line, side, c, tf, name):
    n = len(df)
    if n < 30:
        return None
    lo, hi, cl, op, sg = arrays(df, side)
    ln = np.asarray(line, dtype=float) * sg
    a = float(atr(df).iloc[-1]); vol = df["volume"].to_numpy()
    for f in range(n - 1, max(n - 1 - c["lookback_bars"], c["pre_below_bars"] + 1) - 1, -1):
        if not (cl[f] > ln[f] and cl[f - 1] <= ln[f - 1]):
            continue
        pre = cl[f - c["pre_below_bars"]:f] <= ln[f - c["pre_below_bars"]:f]
        if not pre.all():
            continue
        if (cl[f:] <= ln[f:]).any():
            return None
        buf = max(c["stop_buf_atr"] * a, abs(ln[-1]) * 0.0003)
        touched = f < n - 1 and lo[-1] <= ln[-1] + abs(ln[-1]) * c["retest_tol_pct"] / 100 and cl[-1] > ln[-1]
        stop = (min(lo[-3:]) - buf) * sg
        st = "ACTIVE" if touched else "PENDING"
        return mk("T4", tf, side, st, cl[-1] * sg, "MARKET", stop, ln[-1] * sg, name, [], vol_ratio(vol, f, n - 1))
    return None


def trendline(df, side, k, min_sep):
    """Garis dari 2 pivot terakhir: long = garis turun dari pivot high; short = garis naik dari pivot low."""
    hi, lo = pivots(df, k)
    pts = hi if side == "long" else lo
    if len(pts) < 2:
        return None
    (p1, v1), (p2, v2) = pts[-2], pts[-1]
    if p2 - p1 < min_sep or (side == "long" and v2 >= v1) or (side == "short" and v2 <= v1):
        return None
    slope = (v2 - v1) / (p2 - p1)
    return v1 + slope * (np.arange(len(df)) - p1)


def flips(closed, side, c):
    out = []
    for tf in c["tfs"]:
        df = closed[tf]
        for p in c["ema_periods"]:
            r = flip_retest(df, ema(df["close"], p).to_numpy(), side, c, tf, f"EMA{p}_flip")
            if r:
                out.append(r)
        tl = trendline(df, side, c["pivot_k"], c["min_line_sep"])
        if tl is not None:
            r = flip_retest(df, tl, side, c, tf, "trendline_reclaim")
            if r:
                out.append(r)
    return out
