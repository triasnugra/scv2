"""Gate 7 - invalidasi, R:R bersih biaya, ukuran posisi."""
from __future__ import annotations
from .util import cost_pct


def check(cand, cfg, is_major, restr, counter, equity) -> dict:
    g = cfg["g7"]; e, s = cand["entry"], cand["stop"]; sg = 1 if cand["side"] == "long" else -1
    cost = cost_pct(cfg); why = []
    stop_pct = abs(e - s) / e * 100
    if sg * (e - s) <= 0:
        why.append("stop di sisi salah")
    mx = g["max_stop_pct_major"] if is_major else g["max_stop_pct_alt"]
    if stop_pct > mx:
        why.append(f"stop {stop_pct:.2f}% > batas {mx}% (bukan scalp)")
    if stop_pct < g["min_stop_pct"]:
        why.append(f"stop {stop_pct:.2f}% terlalu rapat (habis oleh biaya)")
    risk_unit = stop_pct + cost

    def rr(t):
        return None if t is None else (abs(t - e) / e * 100 - cost) / risk_unit
    rr1, rr2 = rr(cand.get("tp1")), rr(cand.get("tp2"))
    if rr1 is None:
        why.append("tidak ada target level searah")
    elif rr1 < g["min_rr_tp1"]:
        why.append(f"R:R TP1 {rr1:.2f} < {g['min_rr_tp1']} (setelah biaya)")
    if rr1 is not None and (rr2 is None or rr2 < g["min_rr_tp2"]):
        why.append("R:R TP2 tidak memenuhi minimum")
    risk = g["risk_pct"] * restr.get("risk_mult", 1.0) * (0.5 if counter else 1.0)
    lev = risk / risk_unit
    if lev > g["max_leverage"]:
        lev = g["max_leverage"]; risk = lev * risk_unit
    notional = equity * lev
    return {"ok": not why, "reasons": why, "stop_pct": round(stop_pct, 3), "cost_pct": round(cost, 3),
            "rr_tp1": None if rr1 is None else round(rr1, 2), "rr_tp2": None if rr2 is None else round(rr2, 2),
            "risk_pct": round(risk, 3), "leverage_effective": round(lev, 2),
            "notional": round(notional, 2), "qty": round(notional / e, 6)}
