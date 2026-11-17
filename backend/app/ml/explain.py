"""Why did the model rank a stock where it did?

Occlusion over the four information sources the model fuses: for every seed we
re-run the forward pass with one source switched off and see how the ensemble
rank and score move.

* market      the Conv3D market-cube embedding -> zeros
* timeseries  the stock's own 16-day indicator sequence embedding -> zeros
* news        news mask -> 0 (as if no article)
* sector      sector graph -> identity (no propagation between peers)
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn

from .features import percentile_in_cross_section
from .marketmoe import MarketMoE
from .predictor import EnsembleResult, Predictor, combine, seeded_forward

SOURCES = ["market", "timeseries", "news", "sector"]
SOURCE_LABELS = {
    "market": "Bức tranh toàn thị trường",
    "timeseries": "Diễn biến giá của chính mã",
    "news": "Tin tức",
    "sector": "Nhóm ngành",
}
FEATURE_LABELS = {
    "ret_1d": "Lợi suất 1 phiên",
    "ret_5d": "Lợi suất 5 phiên",
    "ret_10d": "Lợi suất 10 phiên",
    "rsi": "RSI (14)",
    "macd": "MACD (12, 26)",
    "close_open_ratio": "Đóng so với mở cửa",
    "high_low_ratio": "Biên độ trong phiên",
}


class _Zeros(nn.Module):
    def __init__(self, n: int, f: int):
        super().__init__()
        self.n, self.f = n, f

    def forward(self, x):
        return torch.zeros(x.shape[0], self.n, self.f, dtype=x.dtype, device=x.device)


@contextmanager
def _ablate(model: MarketMoE, source: str):
    f_dim = model.context_proj.in_features
    saved = None
    try:
        if source == "market":
            saved = model.market_conv
            model.market_conv = _Zeros(model.N, f_dim)
        elif source == "timeseries":
            saved = model.ts_proj
            model.ts_proj = _Zeros(model.N, f_dim)
        elif source == "sector":
            saved = model.A_norm.clone()
            model.A_norm.copy_(torch.eye(model.N, dtype=saved.dtype, device=saved.device))
        yield
    finally:
        if source == "market":
            model.market_conv = saved
        elif source == "timeseries":
            model.ts_proj = saved
        elif source == "sector":
            model.A_norm.copy_(saved)


@dataclass
class Ablations:
    full: EnsembleResult
    by_source: dict[str, EnsembleResult]


def run_ablations(pred: Predictor, x: np.ndarray, news_emb: np.ndarray, news_mask: np.ndarray) -> Ablations:
    xt, et, mt = pred._tensors(x, news_emb, news_mask)
    seed = pred.art.noise_seed
    full = combine(np.stack([seeded_forward(m, xt, et, mt, seed)[0].numpy() for m in pred.models]))
    out = {}
    for src in SOURCES:
        scores = []
        for m in pred.models:
            mask = torch.zeros_like(mt) if src == "news" else mt
            with _ablate(m, src):
                scores.append(seeded_forward(m, xt, et, mask, seed)[0].numpy())
        out[src] = combine(np.stack(scores))
    return Ablations(full, out)


def feature_label(feat: str, value: float, pct: float) -> str | None:
    if np.isnan(value):
        return None
    if feat == "rsi":
        if value >= 70:
            return "quá mua"
        if value <= 30:
            return "quá bán"
    if feat in ("ret_1d", "ret_5d", "ret_10d"):
        if pct >= 0.9:
            return "thuộc nhóm tăng mạnh nhất rổ"
        if pct <= 0.1:
            return "thuộc nhóm giảm mạnh nhất rổ"
    if feat == "macd":
        return "xu hướng tăng" if value > 0 else "xu hướng giảm"
    if feat == "high_low_ratio" and pct >= 0.9:
        return "biến động mạnh"
    return None


def explain_all(
    abl: Ablations,
    tickers: list[str],
    sectors: dict[str, str],
    feature_order: list[str],
    raw_last: np.ndarray,
    news_titles: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """Explanation payload for every ticker (stored as JSON)."""
    full = abl.full
    pcts = np.stack([percentile_in_cross_section(raw_last[:, k]) for k in range(len(feature_order))], axis=1)
    n = len(tickers)
    # sector ranks
    by_sector: dict[str, list[int]] = {}
    for j, t in enumerate(tickers):
        by_sector.setdefault(sectors.get(t, "Khác"), []).append(j)

    payloads = {}
    for j, t in enumerate(tickers):
        sources = {}
        for src, res in abl.by_source.items():
            sources[src] = {
                "label": SOURCE_LABELS[src],
                "delta_score": float(full.score[j] - res.score[j]),
                "rank_without": int(res.rank[j]),
                "rank_shift": int(res.rank[j] - full.rank[j]),  # >0: without it the stock falls
            }
        features = {}
        for k, feat in enumerate(feature_order):
            v = float(raw_last[j, k])
            p = float(pcts[j, k])
            features[feat] = {
                "label": FEATURE_LABELS.get(feat, feat),
                "value": None if np.isnan(v) else v,
                "percentile": None if np.isnan(p) else p,
                "note": feature_label(feat, v, p),
            }
        sec = sectors.get(t, "Khác")
        members = sorted(by_sector[sec], key=lambda i: full.rank[i])
        best = max(sources, key=lambda s: sources[s]["rank_shift"])
        top_driver = best if sources[best]["rank_shift"] > 0 else None
        payload = {
            "rank": int(full.rank[j]),
            "n": n,
            "score": float(full.score[j]),
            "score_std": float(full.score_std[j]),
            "votes": int(full.votes[j]),
            "seeds": int(full.per_seed.shape[0]),
            "sources": sources,
            "top_driver": top_driver,
            "features": features,
            "sector": {
                "name": sec,
                "rank_in_sector": members.index(j) + 1,
                "n_in_sector": len(members),
                "leaders": [tickers[i] for i in members[:3]],
            },
            "news": (news_titles or {}).get(t),
        }
        payload["summary"] = summarize(t, payload)
        payloads[t] = payload
    return payloads


def summarize(ticker: str, p: dict) -> str:
    parts = [f"Hạng {p['rank']}/{p['n']}, {p['votes']}/{p['seeds']} mô hình xếp vào top 5."]
    if p["top_driver"]:
        drv = p["sources"][p["top_driver"]]
        parts.append(f"Yếu tố đẩy hạng nhiều nhất: {drv['label'].lower()} (bỏ đi thì tụt xuống hạng {drv['rank_without']}).")
    else:
        parts.append("Không nguồn thông tin nào đang kéo mã này lên rõ rệt.")
    notes = [f"{v['label']} {v['note']}" for v in p["features"].values() if v.get("note") and "xu hướng" not in v["note"]]
    if notes:
        text = "; ".join(notes[:2])
        parts.append(text[0].upper() + text[1:] + ".")
    return " ".join(parts)
