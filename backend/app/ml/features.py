"""The 7 technical indicators and their normalisation.

Formulas follow notebook ``midmoe-vn-cube-build`` (Phase 2), which used
pandas-ta 0.4.x. pandas-ta is no longer on PyPI, so RSI and MACD are
re-implemented here with the same conventions:

* RSI(14): Wilder smoothing as ``ewm(alpha=1/14, adjust=False)`` on gains and
  losses, no SMA seed (the notebook printed exactly 1 leading NaN for RSI).
* MACD(12, 26): EMAs seeded with the SMA of the first ``n`` closes, then
  ``ewm(span=n, adjust=False)`` (the notebook printed 25 leading NaNs).
* close_open_ratio = close/open - 1, high_low_ratio = (high - low)/open.

Normalisation (fitted on 2022-2024 and stored in ``vn_norm_params.json``):
clip to [p1, p99], then min-max to [0, 1].
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["ret_1d", "ret_5d", "ret_10d", "rsi", "macd", "close_open_ratio", "high_low_ratio"]


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    diff = close.diff(1)
    gain = diff.clip(lower=0)
    loss = diff.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False).mean()
    denom = avg_gain + avg_loss.abs()
    out = 100 * avg_gain / denom
    return out.where(denom != 0, 50.0).where(diff.notna())


def ema_sma_seeded(close: pd.Series, length: int) -> pd.Series:
    s = close.astype(float).copy()
    if len(s) < length:
        return pd.Series(np.nan, index=close.index)
    seed = s.iloc[:length].mean()
    s.iloc[: length - 1] = np.nan
    s.iloc[length - 1] = seed
    return s.ewm(span=length, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    return ema_sma_seeded(close, fast) - ema_sma_seeded(close, slow)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """One ticker's OHLC rows (any order) -> same rows sorted by date with the 7 indicators added."""
    df = df.sort_values("date").reset_index(drop=True).copy()
    close = df["close"].astype(float)
    df["ret_1d"] = close.pct_change(1)
    df["ret_5d"] = close.pct_change(5)
    df["ret_10d"] = close.pct_change(10)
    df["rsi"] = rsi(close, 14)
    df["macd"] = macd(close)
    df["close_open_ratio"] = close / df["open"] - 1
    df["high_low_ratio"] = (df["high"] - df["low"]) / df["open"]
    return df


def normalize(values: np.ndarray, feature_order: list[str], norm_params: dict) -> np.ndarray:
    """values (..., D) raw -> (..., D) in [0, 1]. NaN stays NaN."""
    out = np.empty_like(values, dtype=np.float32)
    for k, feat in enumerate(feature_order):
        p = norm_params[feat]
        col = np.clip(values[..., k], p["p1"], p["p99"])
        out[..., k] = (col - p["min"]) / (p["max"] - p["min"] + 1e-8)
    return out


def percentile_in_cross_section(values: np.ndarray) -> np.ndarray:
    """(N,) -> fraction of stocks with a value <= this one (0..1), NaN-safe."""
    v = np.asarray(values, dtype=float)
    valid = ~np.isnan(v)
    out = np.full_like(v, np.nan)
    if valid.sum() == 0:
        return out
    ranks = pd.Series(v[valid]).rank(pct=True).to_numpy()
    out[valid] = ranks
    return out
