"""Gate 4 - peta level & confluence."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .indicators import atr, ema
from .structure import pivots, find_impulse, weekly_bars


def _lv(price, kind, family, tf, target=True, lo=None, hi=None):
    return {"price": float(price), "kind": kind, "family": family, "tf": tf, "target_ok": target,
            "lo": float(price if lo is None else lo), "hi": float(price if hi is None else hi)}


def _fvgs(df: pd.DataFrame, tf: str, min_pct: float, n: int = 60):
    d = df.iloc[-n:]; h = d["high"].to_numpy(); l = d["low"].to_numpy(); out = []
    for i in range(2, len(d)):
        if l[i] > h[i - 2] and (l[i] - h[i - 2]) / h[i - 2] * 100 >= min_pct:
            if i + 1 >= len(d) or l[i + 1:].min() > h[i - 2]:
                out.append(_lv((h[i - 2] + l[i]) / 2, "FVG_BULL", "FVG", tf, True, h[i - 2], l[i]))
        elif h[i] < l[i - 2] and (l[i - 2] - h[i]) / h[i] * 100 >= min_pct:
            if i + 1 >= len(d) or h[i + 1:].max() < l[i - 2]:
                out.append(_lv((h[i] + l[i - 2]) / 2, "FVG_BEAR", "FVG", tf, True, h[i], l[i - 2]))
    return out[-3:]


def _zones(df: pd.DataFrame, tf: str, imp_atr: float, n: int = 60):
    d = df.iloc[-n:]; a = atr(df).iloc[-1]
    o = d["open"].to_numpy(); c = d["close"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy(); out = []
    for i in range(1, len(d) - 1):
        body = c[i] - o[i]
        if body >= imp_atr * a and c[i - 1] < o[i - 1] and l[i + 1:].min() > l[i - 1]:
            out.append(_lv((l[i - 1] + o[i - 1]) / 2, "DEMAND", "ZONE", tf, True, l[i - 1], max(o[i - 1], c[i - 1])))
        elif -body >= imp_atr * a and c[i - 1] > o[i - 1] and h[i + 1:].max() < h[i - 1]:
            out.append(_lv((h[i - 1] + o[i - 1]) / 2, "SUPPLY", "ZONE", tf, True, min(o[i - 1], c[i - 1]), h[i - 1]))
    return out[-3:]


def build(closed: dict, cfg: dict, now, rng_info: dict, ob: dict | None = None) -> list:
    c = cfg["g4"]; price = float(closed["5m"]["close"].iloc[-1]); out = []
    for tf, key in (("1H", "range_1h"), ("4H", "range_4h")):
        r = rng_info.get(key)
        if r:
            out += [_lv(r["rh"], f"RH_{tf}", "RANGE", tf), _lv(r["rl"], f"RL_{tf}", "RANGE", tf),
                    _lv(r["mid"], f"MID_{tf}", "RANGE", tf)]
    d1 = closed["1D"]
    out += [_lv(d1["high"].iloc[-1], "PDH", "PD", "1D"), _lv(d1["low"].iloc[-1], "PDL", "PD", "1D")]
    w = weekly_bars(d1, now)
    if len(w):
        out += [_lv(w["high"].iloc[-1], "PWH", "PW", "1W"), _lv(w["low"].iloc[-1], "PWL", "PW", "1W")]
    mon = now.normalize() - pd.Timedelta(days=now.weekday())
    h1 = closed["1H"]; m = h1[(h1.index >= mon) & (h1.index < mon + pd.Timedelta(days=1))]
    if len(m) >= 4:
        out += [_lv(m["high"].max(), "MONDAY_HIGH", "MONDAY", "1H"), _lv(m["low"].min(), "MONDAY_LOW", "MONDAY", "1H")]
    for tf, n in (("4H", 8), ("1H", 6)):
        hi, lo = pivots(closed[tf], c["swing_k"])
        for _, p in hi[-n:] + lo[-n:]:
            out.append(_lv(p, f"SWING_{tf}", "SWING", tf))
    for tf in ("4H", "1D"):
        out += _fvgs(closed[tf], tf, c["fvg_min_pct"])
    out += _zones(closed["4H"], "4H", c["imp_atr"])
    for tf in ("1H", "4H"):
        for side in ("long", "short"):
            imp = find_impulse(closed[tf], side, 3, 1.5, 60)
            if imp:
                rg = imp["H"] - imp["L"]
                for r in c["fib_ratios"]:
                    p = imp["H"] - r * rg if side == "long" else imp["L"] + r * rg
                    out.append(_lv(p, f"FIB_{r}", "FIB", tf))
    for tf in ("1H", "4H"):
        for n in (20, 50):
            out.append(_lv(ema(closed[tf]["close"], n).iloc[-1], f"EMA{n}_{tf}", "EMA", tf, target=False))
    if ob:
        out += walls(ob, price, cfg)
    win = c["window_pct"] / 100
    return [lv for lv in out if abs(lv["price"] - price) / price <= win]


def walls(ob: dict, price: float, cfg: dict) -> list:
    g = cfg["g6"]; out = []
    for side, key in (("BID", "bids"), ("ASK", "asks")):
        rows = [r for r in ob.get(key, []) if abs(r[0] - price) / price <= 0.015]
        if len(rows) < 10:
            continue
        med = float(np.median([r[1] for r in ob[key]]))
        for p, q in rows:
            if med > 0 and q >= g["wall_mult"] * med:
                out.append(_lv(p, f"WALL_{side}", "WALL", "OB", target=False))
    return out


def confluence(price: float, levels: list, cfg: dict):
    t = price * cfg["g4"]["near_tol_pct"] / 100
    fams = sorted({lv["family"] for lv in levels if lv["family"] != "WALL" and lv["lo"] - t <= price <= lv["hi"] + t})
    return len(fams), fams
