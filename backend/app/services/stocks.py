"""Single-stock views."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ml.features import compute_indicators
from ..models import Explanation, News, Prediction, Price
from .common import NotFound, resolve_as_of, ticker_brief, ticker_or_404, tickers_map


def _clean(v):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    return float(v)


def prices(s: Session, symbol: str, days: int = 250) -> list[dict]:
    t = ticker_or_404(s, symbol)
    rows = s.scalars(select(Price).where(Price.ticker == t.symbol).order_by(Price.date.desc()).limit(days + 40)).all()
    if not rows:
        return []
    df = pd.DataFrame([{"date": r.date, "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                        "volume": r.volume} for r in rows])
    df = compute_indicators(df).tail(days)
    out = []
    for r in df.itertuples(index=False):
        out.append({"date": r.date.isoformat(), "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                    "volume": r.volume, "rsi": _clean(r.rsi), "macd": _clean(r.macd), "ret_1d": _clean(r.ret_1d)})
    return out


def rank_history(s: Session, symbol: str, days: int = 120) -> list[dict]:
    t = ticker_or_404(s, symbol)
    rows = s.scalars(select(Prediction).where(Prediction.ticker == t.symbol).order_by(Prediction.as_of.desc()).limit(days)).all()
    return [{"as_of": p.as_of.isoformat(), "rank": p.rank, "votes": p.votes, "score": p.score,
             "realized_return": p.realized_return} for p in reversed(rows)]


def explanation(s: Session, symbol: str, as_of: date | None = None) -> dict:
    t = ticker_or_404(s, symbol)
    d = resolve_as_of(s, as_of)
    e = s.get(Explanation, (d, t.symbol))
    if not e:
        raise NotFound(f"Không có giải thích cho {t.symbol} ngày {d}")
    return {"as_of": d.isoformat(), "symbol": t.symbol, **e.payload}


def news(s: Session, symbol: str, days: int = 30, limit: int = 30) -> list[dict]:
    t = ticker_or_404(s, symbol)
    since = date.today() - timedelta(days=days)
    rows = s.scalars(select(News).where(News.ticker == t.symbol, News.date >= since)
                     .order_by(News.date.desc(), News.id.desc()).limit(limit)).all()
    if not rows:  # fall back to the latest articles whatever their age
        rows = s.scalars(select(News).where(News.ticker == t.symbol).order_by(News.date.desc()).limit(10)).all()
    return [{"date": n.date.isoformat(), "title": n.title, "url": n.url, "source": n.source} for n in rows]


def detail(s: Session, symbol: str) -> dict:
    t = ticker_or_404(s, symbol)
    bars = s.scalars(select(Price).where(Price.ticker == t.symbol).order_by(Price.date.desc()).limit(260)).all()
    last, prev = (bars[0] if bars else None), (bars[1] if len(bars) > 1 else None)
    out = {**ticker_brief(t), "price": None, "ai": None}
    if last:
        closes = [b.close for b in bars]
        out["price"] = {
            "date": last.date.isoformat(), "open": last.open, "high": last.high, "low": last.low, "close": last.close,
            "volume": last.volume, "ref": prev.close if prev else None,
            "change": last.close - prev.close if prev else None,
            "change_pct": last.close / prev.close - 1 if prev else None,
            "high_52w": max(b.high for b in bars), "low_52w": min(b.low for b in bars),
            "avg_volume_20": float(np.mean([b.volume for b in bars[:20]])),
            "ret_1m": closes[0] / closes[min(21, len(closes) - 1)] - 1 if len(closes) > 1 else None,
        }
    try:
        d = resolve_as_of(s)
        p = s.get(Prediction, (d, t.symbol))
        e = s.get(Explanation, (d, t.symbol))
        if p:
            prev_p = s.scalars(select(Prediction).where(Prediction.ticker == t.symbol, Prediction.as_of < d)
                               .order_by(Prediction.as_of.desc()).limit(1)).first()
            out["ai"] = {"as_of": d.isoformat(), "rank": p.rank, "votes": p.votes, "score": p.score,
                         "score_std": p.score_std, "seeds": len(p.per_seed),
                         "rank_change": (prev_p.rank - p.rank) if prev_p else None,
                         "summary": e.payload.get("summary") if e else None}
    except NotFound:
        pass
    return out


def peers(s: Session, symbol: str) -> list[dict]:
    t = ticker_or_404(s, symbol)
    tmap = tickers_map(s)
    same = [x for x in tmap.values() if x.sector == t.sector]
    try:
        d = resolve_as_of(s)
        ranks = {p.ticker: p for p in s.scalars(select(Prediction).where(Prediction.as_of == d)).all()}
    except NotFound:
        ranks = {}
    from .market import board

    b = {r["symbol"]: r for r in board(s)["rows"]} if s.scalar(select(Price.date).limit(1)) else {}
    out = []
    for x in same:
        r, p = b.get(x.symbol, {}), ranks.get(x.symbol)
        out.append({"symbol": x.symbol, "short_name": x.short_name, "close": r.get("close"),
                    "change_pct": r.get("change_pct"), "ai_rank": p.rank if p else None, "ai_votes": p.votes if p else None})
    return sorted(out, key=lambda z: z["ai_rank"] or 999)
