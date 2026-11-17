"""Seed the 2025 out-of-sample history from the Kaggle test cube.

``vn_test_cube.npz`` holds the exact model inputs for every 2025 session
(243 windows) plus the realised next-session return of each stock. Running
the 10 seeds on it reproduces the paper's test predictions, so the
"Hiệu quả gợi ý" page shows real, honest out-of-sample results even before
the live pipeline has run.
"""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..ml.explain import explain_all, run_ablations
from ..models import Explanation, Prediction, PredictionRun
from . import store
from .jobs import _sector_vi, artifacts, get_predictor

log = logging.getLogger(__name__)


def _denormalize_last(x_last: np.ndarray, feature_order: list[str], norm: dict) -> np.ndarray:
    out = np.empty_like(x_last, dtype=np.float64)
    for k, f in enumerate(feature_order):
        p = norm[f]
        out[:, k] = x_last[:, k] * (p["max"] - p["min"]) + p["min"]
    return out


def seed_history(s: Session, limit: int | None = None) -> int:
    art = artifacts()
    pred = get_predictor()
    cube = np.load(art.root / "vn_test_cube.npz", allow_pickle=True)
    wend = [pd.Timestamp(v).date() for v in cube["window_end_date"]]
    n = len(wend) if limit is None else min(limit, len(wend))
    sectors = _sector_vi(art)
    for i in range(n):
        as_of: date = wend[i]
        x = cube["x"][i : i + 1]
        ne, nm = cube["news_emb"][i : i + 1], cube["news_mask"][i : i + 1]
        abl = run_ablations(pred, x, ne, nm)
        raw_last = _denormalize_last(x[0, 0, -1], art.feature_order, art.norm_params)
        payloads = explain_all(abl, art.tickers, sectors, art.feature_order, raw_last)
        res = abl.full
        y = cube["y"][i]
        store.clear_predictions(s, as_of)
        s.add(PredictionRun(as_of=as_of, kind="history", n_news=int(nm.sum()), filled=[]))
        for j, sym in enumerate(art.tickers):
            s.add(Prediction(as_of=as_of, ticker=sym, rank=int(res.rank[j]), avg_rank=float(res.avg_rank[j]),
                             score=float(res.score[j]), score_std=float(res.score_std[j]), votes=int(res.votes[j]),
                             per_seed=[float(v) for v in res.per_seed[:, j]], realized_return=float(y[j])))
            s.add(Explanation(as_of=as_of, ticker=sym, payload=payloads[sym]))
        s.commit()
        if i % 25 == 0:
            log.info("history %s/%s (%s)", i + 1, n, as_of)
    return n
