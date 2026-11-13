"""Batas harian: jumlah trade, rugi harian (R), jeda setelah loss beruntun, trade/jam."""
from __future__ import annotations
import pandas as pd


def check(trades: list, now: pd.Timestamp, cfg: dict, per_hour: int | None = None):
    c = cfg["limits"]; day = now.normalize()
    live = [t for t in trades if t.get("status") not in ("CANCELLED", "EXPIRED")]
    today = [t for t in live if pd.Timestamp(t["ts"]).normalize() == day]
    if len(today) >= c["max_trades_day"]:
        return False, f"batas {c['max_trades_day']} trade/hari tercapai"
    closed = sorted([t for t in live if t.get("status") == "CLOSED" and t.get("exit_ts") and pd.Timestamp(t["exit_ts"]) <= now],
                    key=lambda t: t["exit_ts"])
    pnl = sum(t["r"] for t in closed if pd.Timestamp(t["exit_ts"]).normalize() == day)
    if pnl <= -c["max_daily_loss_r"]:
        return False, f"rugi harian {pnl:.1f}R mencapai batas"
    k = c["pause_after_losses"]
    if len(closed) >= k and all(t["r"] < 0 for t in closed[-k:]):
        if now - pd.Timestamp(closed[-1]["exit_ts"]) < pd.Timedelta(hours=c["pause_hours"]):
            return False, f"jeda {c['pause_hours']} jam setelah {k} loss beruntun"
    if per_hour is not None and sum(1 for t in live if now - pd.Timestamp(t["ts"]) < pd.Timedelta(hours=1)) >= per_hour:
        return False, f"batas {per_hour} trade/jam (Monday)"
    return True, ""
