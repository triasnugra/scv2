"""Gate 3 - rezim (RANGING/TRENDING) & lokasi harga."""
from __future__ import annotations
from .structure import detect_range


def analyze(closed: dict, cfg: dict) -> dict:
    c = cfg["g3"]; out = {}
    for tf in ("1H", "4H"):
        out[tf] = detect_range(closed[tf], c["range_lookback"][tf], c["range_exclude_recent"], c["pivot_k"],
                               c["touch_tol_pct"][tf], c["min_height_pct"], c["max_height_pct"])
    primary = out["1H"] or out["4H"]
    return {"regime": "RANGING" if primary else "TRENDING", "range": primary, "range_1h": out["1H"], "range_4h": out["4H"]}


def _near(price: float, lv: dict, tol: float) -> bool:
    t = price * tol
    return lv["lo"] - t <= price <= lv["hi"] + t


def locate(entry: float, rng: dict | None, levels: list, cfg: dict) -> dict:
    c = cfg["g3"]; tol = cfg["g4"]["near_tol_pct"] / 100
    zone, pct = "OTHER", None
    if rng:
        pct = (entry - rng["rl"]) / (rng["rh"] - rng["rl"]) * 100
        if pct <= c["edge_pct"]:
            zone = "RL"
        elif pct >= 100 - c["edge_pct"]:
            zone = "RH"
        elif c["mid_lo"] <= pct <= c["mid_hi"]:
            zone = "MID"
    near = [lv for lv in levels if lv["family"] != "WALL" and _near(entry, lv, tol)]
    for lv in near:
        if lv["kind"] in ("FIB_0.75", "FIB_0.786") and zone != "MID":
            zone = lv["kind"]
    ok, why = True, None
    if zone == "MID":
        ok, why = False, "harga di tengah range (40-60%): tidak ada edge"
    elif zone == "OTHER" and not near:
        ok, why = False, "lokasi tidak valid: tidak dekat level/tepi range"
    return {"zone": zone, "pct_of_range": None if pct is None else round(pct, 1), "ok": ok, "reason": why, "near_n": len(near)}
