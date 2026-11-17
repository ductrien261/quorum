"""AI picks: daily rankings produced by the model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Explanation, Prediction, PredictionRun
from .common import closes_on, next_session, prev_price_date, previous_run, resolve_as_of, tickers_map


def run_dates(s: Session) -> list[dict]:
    runs = s.scalars(select(PredictionRun).order_by(PredictionRun.as_of)).all()
    return [{"as_of": r.as_of.isoformat(), "kind": r.kind} for r in runs]


def rankings(s: Session, as_of: date | None = None) -> dict:
    d = resolve_as_of(s, as_of)
    run = s.get(PredictionRun, d)
    tmap = tickers_map(s)
    preds = s.scalars(select(Prediction).where(Prediction.as_of == d).order_by(Prediction.rank)).all()
    prev_d = previous_run(s, d)
    prev = {p.ticker: p.rank for p in s.scalars(select(Prediction).where(Prediction.as_of == prev_d)).all()} if prev_d else {}
    expl = {e.ticker: e.payload for e in s.scalars(select(Explanation).where(Explanation.as_of == d)).all()}
    bars, ref_d = closes_on(s, d), prev_price_date(s, d)
    refs = closes_on(s, ref_d) if ref_d else {}
    target, confirmed = next_session(s, d)
    rows = []
    for p in preds:
        t = tmap[p.ticker]
        e = expl.get(p.ticker, {})
        bar, ref = bars.get(p.ticker), refs.get(p.ticker)
        rows.append({
            "symbol": p.ticker, "short_name": t.short_name, "name": t.name, "sector": t.sector,
            "rank": p.rank, "avg_rank": p.avg_rank, "score": p.score, "score_std": p.score_std, "votes": p.votes,
            "rank_change": (prev[p.ticker] - p.rank) if p.ticker in prev else None,
            "close": bar.close if bar else None,
            "change_pct": (bar.close / ref.close - 1) if bar and ref else None,
            "summary": e.get("summary"), "top_driver": e.get("top_driver"),
            "driver_label": e["sources"][e["top_driver"]]["label"] if e and e.get("top_driver") else None,
            "has_news": bool(e.get("news")),
            "realized_return": p.realized_return,
        })
    return {
        "as_of": d.isoformat(), "target_session": target.isoformat(), "target_confirmed": confirmed,
        "kind": run.kind if run else None, "n_news": run.n_news if run else 0, "seeds": len(preds[0].per_seed) if preds else 0,
        "previous_as_of": prev_d.isoformat() if prev_d else None, "rows": rows,
    }


def picks(s: Session, as_of: date | None = None, k: int = 5) -> dict:
    r = rankings(s, as_of)
    rows = r["rows"]
    movers = sorted([x for x in rows if x["rank_change"] is not None], key=lambda x: -x["rank_change"])[:5]
    new_top = [x for x in rows if x["rank"] <= 10 and x["rank_change"] is not None and x["rank"] + x["rank_change"] > 10]
    return {**r, "rows": rows[:k], "movers": movers, "new_in_top10": new_top}
