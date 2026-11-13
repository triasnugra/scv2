"""Struktur pasar: pivot, range, impuls, bar mingguan."""
from __future__ import annotations
import numpy as np
import pandas as pd


def pivots(df: pd.DataFrame, k: int = 2):
    """Pivot terkonfirmasi (butuh k candle setelahnya => tanpa look-ahead)."""
    h = df["high"].to_numpy(); l = df["low"].to_numpy(); n = len(h)
    hi, lo = [], []
    for i in range(k, n - k):
        if h[i] == h[i - k:i + k + 1].max() and h[i] > h[i - 1]:
            hi.append((i, float(h[i])))
        if l[i] == l[i - k:i + k + 1].min() and l[i] < l[i - 1]:
            lo.append((i, float(l[i])))
    return hi, lo


def detect_range(df: pd.DataFrame, look: int, excl: int, k: int, tol_pct: float,
                 hmin: float, hmax: float):
    d = df.iloc[-look:]
    if len(d) < max(30, look // 2):
        return None
    hi, lo = pivots(d, k)
    m = len(d) - excl
    hi = [p for p in hi if p[0] < m]
    lo = [p for p in lo if p[0] < m]
    tol = tol_pct / 100.0

    def clus(pts, top):
        for _, pr in sorted(pts, key=lambda x: x[1], reverse=top):
            g = [q[1] for q in pts if abs(q[1] - pr) / pr <= tol]
            if len(g) >= 2:
                return float(np.mean(g)), len(g)
        return None

    H, L = clus(hi, True), clus(lo, False)
    if not H or not L or H[0] <= L[0]:
        return None
    h = (H[0] - L[0]) / L[0] * 100
    if not (hmin <= h <= hmax):
        return None
    price = float(df["close"].iloc[-1]); ext = (H[0] - L[0]) * 0.5
    if price > H[0] + ext or price < L[0] - ext:
        return None
    return {"rh": H[0], "rl": L[0], "mid": (H[0] + L[0]) / 2, "height_pct": h,
            "touches_h": H[1], "touches_l": L[1]}


def find_impulse(df: pd.DataFrame, side: str, k: int = 3, min_pct: float = 1.5, back: int = 60):
    """Impuls terakhir yang masih utuh. long: swing low -> swing high; short: sebaliknya."""
    hi, lo = pivots(df, k)
    h = df["high"].to_numpy(); l = df["low"].to_numpy()
    if side == "long":
        for pos, H in reversed(hi):
            if h[pos:].max() > H:
                continue
            a = max(0, pos - back)
            j = int(np.argmin(l[a:pos + 1])) + a
            L = float(l[j])
            if j < pos and l[pos:].min() > L and (H - L) / L * 100 >= min_pct:
                return {"H": H, "L": L, "h_pos": pos, "l_pos": j}
    else:
        for pos, L in reversed(lo):
            if l[pos:].min() < L:
                continue
            a = max(0, pos - back)
            j = int(np.argmax(h[a:pos + 1])) + a
            H = float(h[j])
            if j < pos and h[pos:].max() < H and (H - L) / L * 100 >= min_pct:
                return {"H": H, "L": L, "h_pos": j, "l_pos": pos}
    return None


def weekly_bars(d1: pd.DataFrame, now) -> pd.DataFrame:
    """Bar mingguan (Senin-Minggu UTC) dari 1D; hanya minggu yang sudah selesai."""
    if len(d1) == 0:
        return d1.iloc[0:0]
    wk_start = (d1.index - pd.to_timedelta(d1.index.weekday, unit="D")).normalize()
    g = d1.groupby(wk_start).agg(open=("open", "first"), high=("high", "max"),
                                 low=("low", "min"), close=("close", "last"), volume=("volume", "sum"))
    now = pd.Timestamp(now)
    cur = (now.normalize() - pd.Timedelta(days=now.weekday()))
    return g[g.index < cur]
