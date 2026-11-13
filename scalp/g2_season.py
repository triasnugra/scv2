"""Gate 2 - bias tren ("musim") dari 1D & 4H."""
from __future__ import annotations
import pandas as pd
from .indicators import ema
from .structure import pivots, weekly_bars


def _score(df: pd.DataFrame, k: int) -> int:
    s = 0
    hi, lo = pivots(df, k)
    if len(hi) >= 2 and len(lo) >= 2:
        if hi[-1][1] > hi[-2][1] and lo[-1][1] > lo[-2][1]:
            s += 1
        elif hi[-1][1] < hi[-2][1] and lo[-1][1] < lo[-2][1]:
            s -= 1
    c = df["close"]; e20, e50 = ema(c, 20).iloc[-1], ema(c, 50).iloc[-1]
    if c.iloc[-1] > e20 > e50:
        s += 1
    elif c.iloc[-1] < e20 < e50:
        s -= 1
    return s


def _label(total: float, thr: float) -> str:
    return "LONG_SEASON" if total >= thr else "SHORT_SEASON" if total <= -thr else "NEUTRAL_RANGE"


def btc_weekly_support(d1: pd.DataFrame, now, tol_pct: float) -> bool:
    w = weekly_bars(d1, now)
    if len(w) < 6:
        return False
    _, lo = pivots(w, 2)
    price = float(d1["close"].iloc[-1])
    return any(abs(price - p) / p * 100 <= tol_pct and price >= p * 0.99 for _, p in lo[-4:])


def season(closed: dict, cfg: dict, now, btc_closed: dict | None, is_btc: bool) -> dict:
    c = cfg["g2"]
    s1, s4 = _score(closed["1D"], c["pivot_k"]), _score(closed["4H"], c["pivot_k"])
    total = c["w_1d"] * s1 + c["w_4h"] * s4
    own = _label(total, c["threshold"]); label = own; notes = []
    btc_label = None; no_short = False
    ref = closed if is_btc else btc_closed
    if ref is not None:
        if not is_btc:
            b = c["w_1d"] * _score(ref["1D"], c["pivot_k"]) + c["w_4h"] * _score(ref["4H"], c["pivot_k"])
            btc_label = _label(b, c["threshold"])
            if own != "NEUTRAL_RANGE" and btc_label not in ("NEUTRAL_RANGE", own):
                label = "NEUTRAL_RANGE"; notes.append(f"altcoin {own} tapi BTC {btc_label}: diturunkan ke NEUTRAL_RANGE")
        no_short = btc_weekly_support(ref["1D"], now, c["weekly_support_tol_pct"])
        if no_short:
            notes.append("BTC di support mingguan: short dilarang")
    return {"season": label, "own": own, "score_1d": s1, "score_4h": s4, "total": total,
            "btc_season": btc_label, "no_short": no_short, "notes": notes}
