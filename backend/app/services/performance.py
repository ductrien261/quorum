"""Track record of the AI picks.

For every run with known next-session returns:
* top-K  = equal-weight average return of the K highest-ranked stocks
* basket = equal-weight average of all 78 stocks (what picking at random earns on average)
* index  = VN-Index return over the same session, when index data is available

Sharpe ratio follows the paper (daily mean / daily std, not annualised);
the annualised value multiplies by sqrt(252).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import IndexPrice, Prediction, PredictionRun
from ..reference import INDEX_CODE


def _ndcg_at_k(ranks_pred: list[int], returns: list[float], k: int = 5) -> float:
    r = np.asarray(returns)
    order_true = np.argsort(np.argsort(r))
    grades = np.clip((order_true / len(r) * 5).astype(int), 0, 4)
    top = np.argsort(ranks_pred)[:k]
    disc = 1.0 / np.log2(np.arange(2, k + 2))
    dcg = (grades[top] * disc).sum()
    idcg = (np.sort(grades)[::-1][:k] * disc).sum()
    return float(dcg / idcg) if idcg > 0 else 0.0


def _stats(daily: np.ndarray) -> dict:
    if len(daily) == 0:
        return {}
    equity = np.cumprod(1 + daily)
    peak = np.maximum.accumulate(equity)
    sd = daily.std()
    return {
        "total_return": float(equity[-1] - 1),
        "avg_daily": float(daily.mean()),
        "sharpe_daily": float(daily.mean() / sd) if sd > 0 else None,
        "sharpe_annual": float(daily.mean() / sd * np.sqrt(252)) if sd > 0 else None,
        "max_drawdown": float((1 - equity / peak).max()),
        "positive_days": float((daily > 0).mean()),
    }


def track_record(s: Session, start: date | None = None, end: date | None = None, k: int = 5, kind: str | None = None) -> dict:
    q = select(Prediction).where(Prediction.realized_return.is_not(None))
    if start:
        q = q.where(Prediction.as_of >= start)
    if end:
        q = q.where(Prediction.as_of <= end)
    by_day: dict[date, list[Prediction]] = defaultdict(list)
    for p in s.scalars(q).all():
        by_day[p.as_of].append(p)
    kinds = {r.as_of: r.kind for r in s.scalars(select(PredictionRun)).all()}
    idx = {r.date: r.close for r in s.scalars(select(IndexPrice).where(IndexPrice.code == INDEX_CODE)).all()}
    idx_dates = sorted(idx)
    idx_next = {d: idx_dates[i + 1] for i, d in enumerate(idx_dates[:-1])}

    rows = []
    for d in sorted(by_day):
        if kind and kinds.get(d) != kind:
            continue
        ps = by_day[d]
        if len(ps) < 10:
            continue
        ps.sort(key=lambda p: p.rank)
        top = ps[:k]
        rets = [p.realized_return for p in ps]
        n2 = idx_next.get(d)
        rows.append({
            "as_of": d.isoformat(), "kind": kinds.get(d),
            "top": float(np.mean([p.realized_return for p in top])),
            "basket": float(np.mean(rets)),
            "index": (idx[n2] / idx[d] - 1) if n2 and d in idx else None,
            "ndcg": _ndcg_at_k([p.rank for p in ps], rets, k),
            "picks": [{"symbol": p.ticker, "ret": p.realized_return} for p in top],
        })
    top = np.array([r["top"] for r in rows])
    basket = np.array([r["basket"] for r in rows])
    has_idx = [r for r in rows if r["index"] is not None]
    eq_t, eq_b, eq_i = 1.0, 1.0, 1.0
    for r in rows:
        eq_t *= 1 + r["top"]
        eq_b *= 1 + r["basket"]
        if r["index"] is not None:
            eq_i *= 1 + r["index"]
        r["equity_top"], r["equity_basket"] = eq_t, eq_b
        r["equity_index"] = eq_i if has_idx else None
    return {
        "k": k, "n_days": len(rows),
        "from": rows[0]["as_of"] if rows else None, "to": rows[-1]["as_of"] if rows else None,
        "top": _stats(top), "basket": _stats(basket),
        "index": _stats(np.array([r["index"] for r in has_idx])) if len(has_idx) == len(rows) and rows else None,
        "beat_basket_days": float((top > basket).mean()) if rows else None,
        "ndcg": float(np.mean([r["ndcg"] for r in rows])) if rows else None,
        "periods": sorted({r["kind"] for r in rows if r["kind"]}),
        "daily": rows,
    }
