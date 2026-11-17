"""Stock screener over the 78-stock basket: price board + AI rank + indicator snapshot."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Explanation
from .common import NotFound, resolve_as_of
from .market import board


@dataclass
class Filters:
    sectors: list[str] | None = None
    max_rank: int | None = None
    min_votes: int | None = None
    rsi_min: float | None = None
    rsi_max: float | None = None
    change_min: float | None = None  # fraction, e.g. -0.02
    change_max: float | None = None
    ret5_min: float | None = None
    ret5_max: float | None = None
    min_value_bn: float | None = None  # traded value, billion VND
    macd_positive: bool | None = None
    sort: str = "ai_rank"
    limit: int = 78


def screen(s: Session, f: Filters) -> dict:
    b = board(s)
    try:
        d = resolve_as_of(s)
        feats = {e.ticker: e.payload.get("features", {}) for e in s.scalars(select(Explanation).where(Explanation.as_of == d)).all()}
    except NotFound:
        feats = {}
    out = []
    for r in b["rows"]:
        ft = feats.get(r["symbol"], {})
        rsi = (ft.get("rsi") or {}).get("value")
        macd = (ft.get("macd") or {}).get("value")
        ret5 = (ft.get("ret_5d") or {}).get("value")
        row = {**r, "rsi": rsi, "macd": macd, "ret_5d": ret5}
        if f.sectors and r["sector"] not in f.sectors:
            continue
        if f.max_rank and (r.get("ai_rank") or 999) > f.max_rank:
            continue
        if f.min_votes is not None and (r.get("ai_votes") or 0) < f.min_votes:
            continue
        if f.rsi_min is not None and (rsi is None or rsi < f.rsi_min):
            continue
        if f.rsi_max is not None and (rsi is None or rsi > f.rsi_max):
            continue
        cp = r.get("change_pct")
        if f.change_min is not None and (cp is None or cp < f.change_min):
            continue
        if f.change_max is not None and (cp is None or cp > f.change_max):
            continue
        if f.ret5_min is not None and (ret5 is None or ret5 < f.ret5_min):
            continue
        if f.ret5_max is not None and (ret5 is None or ret5 > f.ret5_max):
            continue
        if f.min_value_bn is not None and ((r.get("value") or 0) / 1e9) < f.min_value_bn:
            continue
        if f.macd_positive is not None and (macd is None or (macd > 0) != f.macd_positive):
            continue
        out.append(row)
    keymap = {
        "ai_rank": lambda x: x.get("ai_rank") or 999,
        "change_pct": lambda x: -(x.get("change_pct") or -9),
        "value": lambda x: -(x.get("value") or 0),
        "rsi": lambda x: -(x.get("rsi") or -1),
    }
    out.sort(key=keymap.get(f.sort, keymap["ai_rank"]))
    return {"date": b["date"], "ai_as_of": b["ai_as_of"], "count": len(out), "rows": out[: f.limit]}
