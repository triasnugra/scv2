"""Pengambilan data OHLCV publik (tanpa API key) dengan fallback antar-provider."""
from __future__ import annotations
import time
import requests
import pandas as pd

BINANCE_HOSTS = {"binance_vision": "data-api.binance.vision", "binance": "api.binance.com"}
B_TF = {"5m": "5m", "15m": "15m", "1H": "1h", "4H": "4h", "1D": "1d"}
BY_TF = {"5m": "5", "15m": "15", "1H": "60", "4H": "240", "1D": "D"}
OKX_TF = {"5m": "5m", "15m": "15m", "1H": "1H", "4H": "4H", "1D": "1Dutc"}


def _get(url, params, timeout, tries=2):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "scalp-engine/1.0"})
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa
            last = e
            time.sleep(0.6 * (i + 1))
    raise last


def _page_binance(prov, symbol, tf, limit, end_ms, timeout):
    p = {"symbol": symbol, "interval": B_TF[tf], "limit": min(limit, 1000)}
    if end_ms:
        p["endTime"] = end_ms
    rows = _get(f"https://{BINANCE_HOSTS[prov]}/api/v3/klines", p, timeout)
    return [(int(x[0]), *map(float, x[1:6])) for x in rows]


def _page_bybit(prov, symbol, tf, limit, end_ms, timeout):
    p = {"category": "spot", "symbol": symbol, "interval": BY_TF[tf], "limit": min(limit, 1000)}
    if end_ms:
        p["end"] = end_ms
    j = _get("https://api.bybit.com/v5/market/kline", p, timeout)
    rows = j["result"]["list"]
    return sorted((int(x[0]), *map(float, x[1:6])) for x in rows)


def _page_okx(prov, symbol, tf, limit, end_ms, timeout):
    inst = symbol[:-4] + "-USDT" if symbol.endswith("USDT") else symbol
    p = {"instId": inst, "bar": OKX_TF[tf], "limit": 100}
    if end_ms:
        p["after"] = end_ms + 1
    j = _get("https://www.okx.com/api/v5/market/history-candles", p, timeout)
    rows = [x for x in j["data"] if x[8] == "1"]   # hanya yang sudah confirm
    return sorted((int(x[0]), *map(float, x[1:6])) for x in rows)


def _page(prov, *a):
    if prov in BINANCE_HOSTS:
        return _page_binance(prov, *a)
    if prov == "bybit":
        return _page_bybit(prov, *a)
    if prov == "okx":
        return _page_okx(prov, *a)
    raise ValueError(prov)


def to_df(rows) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume"])
    df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df.drop_duplicates("t").sort_values("t").set_index("t")
    df.index.name = "open_time"
    return df.astype(float)


class Fetcher:
    """Provider pertama yang berhasil dipakai terus (agar harga konsisten antar-TF)."""

    def __init__(self, cfg: dict):
        self.cfg = cfg["data"]
        self.provider: dict[str, str] = {}

    def klines(self, symbol: str, tf: str, count: int, end_ms: int | None = None) -> pd.DataFrame:
        provs = list(self.cfg["providers"])
        if symbol in self.provider:
            provs = [self.provider[symbol]] + [p for p in provs if p != self.provider[symbol]]
        errs = []
        for prov in provs:
            try:
                rows, end = [], end_ms
                while len(rows) < count:
                    chunk = _page(prov, symbol, tf, count - len(rows), end, self.cfg["timeout"])
                    if not chunk:
                        break
                    rows = chunk + rows
                    new_end = chunk[0][0] - 1
                    if end is not None and new_end >= end:
                        break
                    end = new_end
                    if len(chunk) < 5:
                        break
                if rows:
                    self.provider[symbol] = prov
                    return to_df(rows[-count:] if len(rows) > count else rows)
            except Exception as e:  # noqa
                errs.append(f"{prov}: {type(e).__name__}")
        raise RuntimeError(f"gagal ambil {symbol} {tf}: {errs}")

    def frames(self, symbol: str, counts: dict | None = None) -> dict:
        counts = counts or self.cfg["counts"]
        return {tf: self.klines(symbol, tf, counts[tf]) for tf in counts}

    def orderbook(self, symbol: str):
        """Opsional. Mengembalikan {'bids': [[p,q]..], 'asks': [...]} atau None."""
        if not self.cfg.get("orderbook"):
            return None
        for prov in ("binance_vision", "binance"):
            try:
                j = _get(f"https://{BINANCE_HOSTS[prov]}/api/v3/depth", {"symbol": symbol, "limit": 500}, 10, tries=1)
                return {"bids": [[float(p), float(q)] for p, q in j["bids"]],
                        "asks": [[float(p), float(q)] for p, q in j["asks"]]}
            except Exception:  # noqa
                continue
        return None
