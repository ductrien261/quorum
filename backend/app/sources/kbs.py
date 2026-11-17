"""Daily OHLCV from KB Securities (KBS), the source notebook ``midmoe-vn-data-prepare``
used through ``vnstock`` (``Quote(symbol, source='KBS')``).

vnstock is no longer installable from PyPI, so the endpoint is called directly.
Stock prices come in VND and are divided by 1000 (thousand VND), exactly like
vnstock did, so indicators such as MACD match the training scale. Index values
are already in points.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime

import pandas as pd
import requests

log = logging.getLogger(__name__)

BASE = "https://kbbuddywts.kbsec.com.vn/iis-server/investment"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
}
COLUMNS = {"t": "date", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}


class SourceError(RuntimeError):
    pass


def _get(url: str, params: dict, retries: int = 3, timeout: float = 15.0, session: requests.Session | None = None) -> dict:
    s = session or requests
    last = None
    for attempt in range(retries):
        try:
            r = s.get(url, params=params, headers=HEADERS, timeout=timeout)
            if r.status_code == 429:
                raise SourceError("rate limited")
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** attempt * (5 if "rate" in str(e) else 1)
            log.warning("KBS %s lỗi (%s), thử lại sau %ss", url, e, wait)
            time.sleep(wait)
    raise SourceError(f"KBS không phản hồi: {url} ({last})")


def parse_bars(payload: dict, divide: bool) -> pd.DataFrame:
    rows = payload.get("data_day") or []
    if not rows:
        return pd.DataFrame(columns=list(COLUMNS.values()))
    df = pd.DataFrame(rows).rename(columns=COLUMNS)
    df = df[[c for c in COLUMNS.values() if c in df.columns]]
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float) / (1000.0 if divide else 1.0)
    df["volume"] = df["volume"].astype(float)
    return df.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def fetch_daily(symbol: str, start: date, end: date, is_index: bool = False, session: requests.Session | None = None) -> pd.DataFrame:
    kind = "index" if is_index else "stocks"
    url = f"{BASE}/{kind}/{symbol}/data_day"
    params = {"sdate": start.strftime("%d-%m-%Y"), "edate": end.strftime("%d-%m-%Y")}
    df = parse_bars(_get(url, params, session=session), divide=not is_index)
    return df[(df["date"] >= start) & (df["date"] <= end)].reset_index(drop=True)


def fetch_many(symbols: list[str], start: date, end: date, delay: float = 0.4) -> pd.DataFrame:
    frames = []
    with requests.Session() as s:
        for sym in symbols:
            try:
                df = fetch_daily(sym, start, end, session=s)
                frames.append(df.assign(ticker=sym))
            except SourceError as e:
                log.error("Bỏ qua %s: %s", sym, e)
            time.sleep(delay)
    if not frames:
        return pd.DataFrame(columns=["ticker", *COLUMNS.values()])
    return pd.concat(frames, ignore_index=True)


def today_vn() -> date:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
