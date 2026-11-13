"""Sinyal -> catatan jurnal paper-trade (dipakai live & backtest)."""
from __future__ import annotations


def make_signal(o: dict) -> dict:
    L, S, T = o["levels"], o["size"], o["trigger"]
    side = "long" if o["decision"] == "LONG_SCALP" else "short"
    ts = o["timestamp"]
    return {"id": f"{o['symbol']}-{ts[:16].replace(':', '').replace('-', '')}-{side}-{T['type']}", "ts": ts,
            "symbol": o["symbol"], "side": side, "trigger": T["type"], "tf": T.get("tf"), "level": T.get("level"),
            "entry": L["entry"], "entry_type": T["entry_type"], "stop": L["stop"], "tp1": L["tp1"], "tp2": L["tp2"],
            "stop_pct": L["stop_pct"], "cost_pct": o["cost_pct"], "rr_tp1": L["rr_tp1"], "rr_tp2": L["rr_tp2"],
            "score": o["score"], "risk_pct": S["risk_pct"], "leverage": S["leverage_effective"],
            "notional": S["notional"], "qty": S["qty"], "counter_trend": o.get("counter_trend", False),
            "status": "PENDING"}
