"""Gate 1 - konteks waktu & event. Hasil: PASS | RESTRICT | STAND_ASIDE."""
from __future__ import annotations
import pandas as pd
from .util import TF_DELTA


def auto_events(now: pd.Timestamp, c: dict) -> list[dict]:
    mon = now.normalize() - pd.Timedelta(days=now.weekday())
    m0 = now.normalize().replace(day=1)
    m1 = (m0 + pd.Timedelta(days=32)).replace(day=1)
    w, m = c["weekly_close_window_min"], c["monthly_close_window_min"]
    ev = [{"name": "penutupan mingguan", "ts": b, "before_min": w, "after_min": w} for b in (mon, mon + pd.Timedelta(days=7))]
    ev += [{"name": "penutupan bulanan", "ts": b, "before_min": m, "after_min": m} for b in (m0, m1)]
    return ev


def shock_age_hours(h1: pd.DataFrame, now: pd.Timestamp, move_thr: float, flash_thr: float):
    c = h1["close"].to_numpy(); hi = h1["high"].to_numpy(); lo = h1["low"].to_numpy()
    n = len(c); last = None; prev = False
    for i in range(max(24, n - 96), n):
        hit = abs(c[i] / c[i - 24] - 1) * 100 >= move_thr or (hi[i] - lo[i]) / lo[i] * 100 >= flash_thr
        if hit and not prev:
            last = i
        prev = hit
    if last is None:
        return None
    return (now - (h1.index[last] + TF_DELTA["1H"])) / pd.Timedelta(hours=1)


def check(closed: dict, cfg: dict, now: pd.Timestamp, events: list, is_major: bool) -> dict:
    c = cfg["g1"]; reasons = []; restr = {}; status = "PASS"
    for ev in list(events) + auto_events(now, c):
        t = ev["ts"]
        if t - pd.Timedelta(minutes=ev["before_min"]) <= now <= t + pd.Timedelta(minutes=ev["after_min"]):
            status = "STAND_ASIDE"; reasons.append(f"dekat event: {ev['name']}")
    h1 = closed["1H"]
    qv = h1["close"] * h1["volume"]
    ratio = float(qv.iloc[-6:].mean() / qv.iloc[-168:].mean()) if len(qv) >= 24 else 1.0
    thr = c["thin_ratio_weekend"] if now.weekday() >= 5 else c["thin_ratio"]
    thin = ratio < thr
    if thin:
        status = "STAND_ASIDE"; reasons.append(f"likuiditas tipis (rasio vol {ratio:.2f} < {thr})")
    cls = "major" if is_major else "alt"
    age = shock_age_hours(h1, now, c["shock_pct"][cls], c["flash_bar_pct"][cls])
    if age is not None:
        if age < c["shock_stand_aside_hours"]:
            status = "STAND_ASIDE"; reasons.append(f"pasca dump/pump besar ({age:.0f} jam lalu): tunggu")
        elif age < c["shock_restrict_hours"] and status != "STAND_ASIDE":
            status = "RESTRICT"; restr.update({"triggers": ["T1"], "tfs": ["15m"], "risk_mult": 0.5, "edge_only": True})
            reasons.append(f"pasca dump/pump ({age:.0f} jam lalu): hanya T1 15m di tepi range, ukuran 0.5x")
    if now.weekday() == 0 and status != "STAND_ASIDE":
        status = "RESTRICT"
        restr.update({"min_confluence": c["monday_min_confluence"], "max_trades_per_hour": c["monday_max_trades_per_hour"]})
        reasons.append("Monday range sedang terbentuk: hanya level penting, maks 2 trade/jam")
    return {"status": status, "restrictions": restr, "reasons": reasons, "thin": thin, "vol_ratio": ratio}
