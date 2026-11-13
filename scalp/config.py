from __future__ import annotations
import copy
import yaml
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else ROOT / "config" / "config.yaml"
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_events(cfg: dict) -> list[dict]:
    p = ROOT / cfg["g1"]["events_file"]
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        raw = (yaml.safe_load(f) or {}).get("events", []) or []
    out = []
    for e in raw:
        ts = pd.Timestamp(e["ts"])
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        out.append({"name": e.get("name", "event"), "ts": ts,
                    "before_min": e.get("before_min", cfg["g1"]["event_before_min"]),
                    "after_min": e.get("after_min", cfg["g1"]["event_after_min"])})
    return out


def clone(cfg: dict) -> dict:
    return copy.deepcopy(cfg)
