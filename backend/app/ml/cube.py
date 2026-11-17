"""Build the model input for one trading day.

Mirrors notebook ``midmoe-vn-cube-build`` Phase 4-6:
indicators per ticker -> market image (dates x 78 x 7) over the union of
trading dates -> normalise -> forward-fill, then back-fill only the warm-up ->
the last 16 sessions ending at ``as_of``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from .artifacts import Artifacts
from .features import compute_indicators, normalize


@dataclass
class MarketImage:
    dates: list[date]
    raw: np.ndarray  # (n_days, N, D) raw indicators, NaN where missing
    norm: np.ndarray  # (n_days, N, D) normalised + filled
    missing: np.ndarray  # (n_days, N) True where the ticker had no bar that day


@dataclass
class DayInput:
    as_of: date
    window_dates: list[date]
    x: np.ndarray  # (1, 1, T, N, D)
    raw_last: np.ndarray  # (N, D) raw indicators on as_of (for explanations)
    filled_tickers: list[str] = field(default_factory=list)  # tickers forward-filled on as_of


def build_market_image(prices: pd.DataFrame, art: Artifacts) -> MarketImage:
    """prices: long frame with ticker, date, open, high, low, close (volume optional)."""
    feats = art.feature_order
    tickers = art.tickers
    frames = []
    for t in tickers:
        sub = prices[prices["ticker"] == t]
        if sub.empty:
            continue
        frames.append(compute_indicators(sub).assign(ticker=t))
    if not frames:
        raise ValueError("Không có dữ liệu giá cho mã nào trong rổ")
    ind = pd.concat(frames, ignore_index=True)
    ind["date"] = pd.to_datetime(ind["date"]).dt.date
    all_dates = sorted(ind["date"].unique())
    d_idx = {d: i for i, d in enumerate(all_dates)}
    t_idx = {t: j for j, t in enumerate(tickers)}

    raw = np.full((len(all_dates), len(tickers), len(feats)), np.nan, dtype=np.float32)
    rows = ind["date"].map(d_idx).to_numpy()
    cols = ind["ticker"].map(t_idx).to_numpy()
    raw[rows, cols, :] = ind[feats].to_numpy(dtype=np.float32)
    missing = np.ones((len(all_dates), len(tickers)), dtype=bool)
    missing[rows, cols] = False

    norm = normalize(raw, feats, art.norm_params)
    for j in range(len(tickers)):
        norm[:, j, :] = pd.DataFrame(norm[:, j, :]).ffill().bfill().to_numpy()
    norm = np.nan_to_num(norm, nan=0.5)  # a ticker with no data at all: neutral mid value
    return MarketImage(all_dates, raw, norm, missing)


def day_input(img: MarketImage, as_of: date, art: Artifacts) -> DayInput:
    T = art.window
    if as_of not in img.dates:
        raise ValueError(f"{as_of} không phải phiên giao dịch có trong dữ liệu")
    end = img.dates.index(as_of)
    if end + 1 < T:
        raise ValueError(f"Cần ít nhất {T} phiên trước {as_of}")
    window = img.norm[end - T + 1 : end + 1]
    filled = [art.tickers[j] for j in np.where(img.missing[end])[0]]
    return DayInput(
        as_of=as_of,
        window_dates=img.dates[end - T + 1 : end + 1],
        x=window[None, None].astype(np.float32),
        raw_last=img.raw[end],
        filled_tickers=filled,
    )
