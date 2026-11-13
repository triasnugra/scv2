"""Ringkasan teks Bahasa Indonesia, skenario bersyarat, statistik."""
from __future__ import annotations


def scenarios(season, rg, levels, closed, cfg) -> list:
    out = []; r = rg.get("range")
    if r:
        L = lambda x: f"{x:.6g}"
        if season in ("LONG_SEASON", "NEUTRAL_RANGE"):
            out.append(f"Di bawah RL {L(r['rl'])} lalu close kembali di atas -> bias long scalp. Aktivasi = T1 (deviasi+reclaim). Invalidasi = reclaim gagal / stop di bawah ekstrem spike.")
        if season in ("SHORT_SEASON", "NEUTRAL_RANGE"):
            out.append(f"Di atas RH {L(r['rh'])} lalu close kembali di bawah -> bias short scalp. Aktivasi = T1. Invalidasi = reclaim gagal / stop di atas ekstrem spike.")
        if season == "LONG_SEASON":
            out.append(f"Close 1H di atas RH {L(r['rh'])} dengan volume lalu retest -> long scalp (T2). Invalidasi = close kembali ke dalam range.")
        if season == "SHORT_SEASON":
            out.append(f"Close 1H di bawah RL {L(r['rl'])} dengan volume lalu retest -> short scalp (T2). Invalidasi = close kembali ke dalam range.")
    elif season != "NEUTRAL_RANGE":
        f = [lv for lv in levels if lv["kind"] in ("FIB_0.75", "FIB_0.786")]
        if f:
            side = "long" if season == "LONG_SEASON" else "short"
            ps = sorted(lv["price"] for lv in f)
            out.append(f"Pullback ke zona Fib 0.75-0.786 (~{ps[0]:.6g}-{ps[-1]:.6g}) dengan stop run kecil + reclaim -> {side} scalp (T3).")
    return out[:2]


def summary(o: dict) -> str:
    d = o["decision"]; lines = [f"{o['symbol']}: {d} | musim {o.get('season')} | rezim {o.get('regime')}"]
    if d in ("LONG_SCALP", "SHORT_SCALP", "WAIT") and o["levels"]["entry"]:
        L = o["levels"]
        lines.append(f"{o['trigger']['type']} {o['trigger'].get('tf','')} ({o['trigger']['status']}) entry {L['entry']:.6g} stop {L['stop']:.6g} "
                     f"TP1 {L['tp1']:.6g} TP2 {L['tp2'] if L['tp2'] is None else format(L['tp2'], '.6g')}")
        lines.append(f"stop {L['stop_pct']}% | R:R {L['rr_tp1']}/{L['rr_tp2']} | skor {o['score']}")
    lines.append("Alasan: " + "; ".join(o["reasons"][:2]) if o["reasons"] else "Alasan: -")
    lines.append("Gate: " + " ".join(f"{k}={v}" for k, v in o["gates"].items()))
    return "\n".join(lines[:5])


def stats(trades: list) -> dict:
    cl = [t for t in trades if t.get("status") == "CLOSED"]
    if not cl:
        return {"n": 0}
    rs = [t["r"] for t in cl]; wins = [r for r in rs if r > 0]; loss = [r for r in rs if r <= 0]
    eq = peak = dd = 0.0
    for t in sorted(cl, key=lambda t: t["exit_ts"]):
        eq += t["r"]; peak = max(peak, eq); dd = max(dd, peak - eq)
    pf = (sum(wins) / -sum(loss)) if loss and sum(loss) < 0 else None
    return {"n": len(cl), "win_rate": round(len(wins) / len(cl) * 100, 1), "expectancy_r": round(sum(rs) / len(rs), 3),
            "total_r": round(sum(rs), 2), "max_dd_r": round(dd, 2), "profit_factor": None if pf is None else round(pf, 2)}
