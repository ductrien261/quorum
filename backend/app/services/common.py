from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Price, PredictionRun, Ticker


class NotFound(Exception):
    pass


def resolve_as_of(s: Session, requested: date | None = None) -> date:
    """Latest prediction run on or before ``requested`` (default: the latest run)."""
    q = select(func.max(PredictionRun.as_of))
    if requested:
        q = q.where(PredictionRun.as_of <= requested)
    d = s.scalar(q)
    if d is None:
        raise NotFound("Chưa có dữ liệu gợi ý. Chạy pipeline trước (xem README).")
    return d


def previous_run(s: Session, as_of: date) -> date | None:
    return s.scalar(select(func.max(PredictionRun.as_of)).where(PredictionRun.as_of < as_of))


def next_session(s: Session, d: date) -> tuple[date, bool]:
    """Next trading session after ``d``. Returns (date, confirmed) where confirmed means a price bar exists."""
    nxt = s.scalar(select(func.min(Price.date)).where(Price.date > d))
    if nxt:
        return nxt, True
    n = d + timedelta(days=1)
    while n.weekday() >= 5:
        n += timedelta(days=1)
    return n, False


def latest_price_date(s: Session) -> date | None:
    return s.scalar(select(func.max(Price.date)))


def tickers_map(s: Session) -> dict[str, Ticker]:
    return {t.symbol: t for t in s.scalars(select(Ticker).order_by(Ticker.sort_order)).all()}


def ticker_or_404(s: Session, symbol: str) -> Ticker:
    t = s.get(Ticker, symbol.upper())
    if not t:
        raise NotFound(f"Mã {symbol.upper()} không nằm trong rổ 78 mã mà mô hình theo dõi.")
    return t


def ticker_brief(t: Ticker) -> dict:
    return {"symbol": t.symbol, "short_name": t.short_name, "name": t.name, "sector": t.sector, "exchange": t.exchange}


def closes_on(s: Session, d: date) -> dict[str, Price]:
    return {p.ticker: p for p in s.scalars(select(Price).where(Price.date == d)).all()}


def prev_price_date(s: Session, d: date) -> date | None:
    return s.scalar(select(func.max(Price.date)).where(Price.date < d))
