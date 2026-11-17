"""Price board and market overview."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import IndexPrice, Prediction, Price
from ..reference import INDEX_CODE, PRICE_LIMIT
from .common import NotFound, closes_on, latest_price_date, prev_price_date, previous_run, resolve_as_of, tickers_map


def _ai_maps(s: Session, as_of: date | None):
    if as_of is None:
        return {}, {}
    cur = {p.ticker: p for p in s.scalars(select(Prediction).where(Prediction.as_of == as_of)).all()}
    prev_d = previous_run(s, as_of)
    prev = {p.ticker: p.rank for p in s.scalars(select(Prediction).where(Prediction.as_of == prev_d)).all()} if prev_d else {}
    return cur, prev


def _sparklines(s: Session, d: date, n: int = 30) -> dict[str, list[float]]:
    """Closes of the last ``n`` sessions up to ``d`` for every ticker (for the board's mini charts)."""
    start = s.scalar(select(Price.date).where(Price.date <= d).distinct().order_by(Price.date.desc()).offset(n - 1).limit(1))
    q = select(Price.ticker, Price.close).where(Price.date <= d).order_by(Price.date)
    if start:
        q = q.where(Price.date >= start)
    out: dict[str, list[float]] = defaultdict(list)
    for sym, close in s.execute(q):
        out[sym].append(round(close, 2))
    return out


def board(s: Session, on: date | None = None) -> dict:
    d = on or latest_price_date(s)
    if d is None:
        raise NotFound("Chưa có dữ liệu giá. Chạy `python -m app.cli prices` trước.")
    pd_ = prev_price_date(s, d)
    today, prev = closes_on(s, d), closes_on(s, pd_) if pd_ else {}
    try:
        ai_as_of = resolve_as_of(s, d)
    except NotFound:
        ai_as_of = None
    ai, ai_prev = _ai_maps(s, ai_as_of)
    spark = _sparklines(s, d)
    rows = []
    for sym, t in tickers_map(s).items():
        bar = today.get(sym)
        ref = prev[sym].close if sym in prev else None
        limit = PRICE_LIMIT.get(t.exchange, 0.07)
        row = {
            "symbol": sym, "short_name": t.short_name, "sector": t.sector, "exchange": t.exchange,
            "ref": ref, "ceiling": round(ref * (1 + limit), 2) if ref else None,
            "floor": round(ref * (1 - limit), 2) if ref else None,
            "open": bar.open if bar else None, "high": bar.high if bar else None, "low": bar.low if bar else None,
            "close": bar.close if bar else None, "volume": bar.volume if bar else None,
            "change": (bar.close - ref) if bar and ref else None,
            "change_pct": (bar.close / ref - 1) if bar and ref else None,
            "value": (bar.close * bar.volume * 1000) if bar else None,  # VND (price is in thousand VND)
            "spark": spark.get(sym, []),
        }
        p = ai.get(sym)
        if p:
            row.update({"ai_rank": p.rank, "ai_votes": p.votes, "ai_score": p.score,
                        "ai_rank_change": (ai_prev[sym] - p.rank) if sym in ai_prev else None})
        rows.append(row)
    return {"date": d.isoformat(), "ref_date": pd_.isoformat() if pd_ else None,
            "ai_as_of": ai_as_of.isoformat() if ai_as_of else None, "rows": rows}


def index_series(s: Session, days: int = 250, code: str = INDEX_CODE) -> list[dict]:
    rows = s.scalars(select(IndexPrice).where(IndexPrice.code == code).order_by(IndexPrice.date.desc()).limit(days)).all()
    return [{"date": r.date.isoformat(), "open": r.open, "high": r.high, "low": r.low, "close": r.close,
             "volume": r.volume} for r in reversed(rows)]


def overview(s: Session) -> dict:
    b = board(s)
    rows = [r for r in b["rows"] if r["change_pct"] is not None]
    up = sum(r["change_pct"] > 0.0005 for r in rows)
    down = sum(r["change_pct"] < -0.0005 for r in rows)
    ceil = sum(r["close"] is not None and r["ceiling"] is not None and r["close"] >= r["ceiling"] - 0.05 for r in rows)
    floor = sum(r["close"] is not None and r["floor"] is not None and r["close"] <= r["floor"] + 0.05 for r in rows)
    sectors: dict[str, dict] = defaultdict(lambda: {"n": 0, "chg": 0.0, "value": 0.0, "ai_rank": 0.0, "n_ai": 0, "symbols": []})
    for r in b["rows"]:
        sec = sectors[r["sector"]]
        sec["n"] += 1
        sec["symbols"].append({"symbol": r["symbol"], "change_pct": r["change_pct"], "value": r["value"],
                               "ai_rank": r.get("ai_rank")})
        if r["change_pct"] is not None:
            sec["chg"] += r["change_pct"]
            sec["value"] += r["value"] or 0
        if r.get("ai_rank"):
            sec["ai_rank"] += r["ai_rank"]
            sec["n_ai"] += 1
    sector_list = [
        {"sector": k, "n": v["n"], "avg_change_pct": v["chg"] / v["n"] if v["n"] else None, "value": v["value"],
         "avg_ai_rank": v["ai_rank"] / v["n_ai"] if v["n_ai"] else None, "symbols": v["symbols"]}
        for k, v in sectors.items()
    ]
    sector_list.sort(key=lambda x: -(x["value"] or 0))
    ranked = sorted(rows, key=lambda r: r["change_pct"])
    idx = index_series(s, 250)
    idx_last = idx[-1] if idx else None
    idx_prev = idx[-2] if len(idx) > 1 else None
    return {
        "date": b["date"],
        "index": {
            "code": INDEX_CODE, "series": idx,
            "close": idx_last["close"] if idx_last else None,
            "change": (idx_last["close"] - idx_prev["close"]) if idx_last and idx_prev else None,
            "change_pct": (idx_last["close"] / idx_prev["close"] - 1) if idx_last and idx_prev else None,
        },
        "breadth": {"up": up, "down": down, "flat": len(rows) - up - down, "ceiling": ceil, "floor": floor},
        "total_value": sum(r["value"] or 0 for r in rows),
        "sectors": sector_list,
        "gainers": [_mini(r) for r in ranked[::-1][:6]],
        "losers": [_mini(r) for r in ranked[:6]],
        "most_active": [_mini(r) for r in sorted(rows, key=lambda r: -(r["value"] or 0))[:6]],
    }


def _mini(r: dict) -> dict:
    return {k: r.get(k) for k in ("symbol", "short_name", "close", "change_pct", "value", "ai_rank")}
