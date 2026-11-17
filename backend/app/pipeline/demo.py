"""Synthetic prices for offline development (``python -m app.cli demo``).

Generates plausible daily bars for the 78 tickers and VN-Index (market +
sector + idiosyncratic factors, HOSE ±7% limits) so the web app can be built
and tested without network access. The model still runs for real on these
inputs. Never use this on the database you present: the UI shows a banner
whenever demo data is loaded.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..models import PipelineLog
from ..reference import INDEX_CODE
from . import store
from .jobs import artifacts

BASE_PRICE = {
    "VCB": 62.0, "BID": 38.0, "CTG": 36.0, "TCB": 24.0, "VPB": 19.0, "MBB": 23.0, "ACB": 25.0, "FPT": 125.0,
    "HPG": 26.0, "VNM": 64.0, "VIC": 42.0, "VHM": 41.0, "MWG": 58.0, "GAS": 70.0, "SAB": 55.0, "SSI": 26.0,
}


def weekdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def generate(start: date, end: date, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    art = artifacts()
    rng = np.random.default_rng(seed)
    days = weekdays(start, end)
    T = len(days)
    sectors = art.sector_of()
    sec_names = sorted(set(sectors.values()))
    market = rng.normal(0.0004, 0.011, T)
    sec_f = {sname: rng.normal(0, 0.008, T) for sname in sec_names}
    frames = []
    for sym in art.tickers:
        beta = rng.uniform(0.7, 1.4)
        vol = rng.uniform(0.010, 0.022)
        r = beta * market + sec_f[sectors.get(sym, sec_names[0])] + rng.normal(0, vol, T)
        r = np.clip(r, -0.069, 0.069)
        close = BASE_PRICE.get(sym, float(rng.uniform(8, 90))) * np.cumprod(1 + r)
        prev = np.concatenate([[close[0] / (1 + r[0])], close[:-1]])
        open_ = prev * (1 + rng.normal(0, 0.004, T))
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.006, T)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.006, T)))
        volume = rng.lognormal(14, 0.6, T).round(-2)
        frames.append(pd.DataFrame({"ticker": sym, "date": days, "open": open_.round(2), "high": high.round(2),
                                    "low": low.round(2), "close": close.round(2), "volume": volume}))
    idx_close = 1250 * np.cumprod(1 + market)
    idx_prev = np.concatenate([[idx_close[0]], idx_close[:-1]])
    idx = pd.DataFrame({"date": days, "open": idx_prev, "high": np.maximum(idx_prev, idx_close) * 1.003,
                        "low": np.minimum(idx_prev, idx_close) * 0.997, "close": idx_close,
                        "volume": rng.lognormal(20, 0.3, T)})
    return pd.concat(frames, ignore_index=True), idx


def load_demo(s: Session, start: date, end: date) -> int:
    prices, idx = generate(start, end)
    store.upsert_prices(s, prices)
    store.upsert_index(s, INDEX_CODE, idx)
    s.add(PipelineLog(job="demo-data", status="success", message="Đã nạp dữ liệu giá giả lập"))
    s.commit()
    return len(prices)
