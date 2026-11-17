"""Database helpers shared by the pipeline jobs."""

from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..ml.artifacts import Artifacts
from ..models import IndexPrice, News, PipelineLog, Price, Ticker
from ..reference import COMPANIES, EXCHANGE, SECTOR_VI


def seed_tickers(s: Session, art: Artifacts) -> int:
    sectors = art.sector_of()
    for i, sym in enumerate(art.tickers):
        short, full = COMPANIES.get(sym, (sym, sym))
        en = sectors.get(sym, "Other")
        s.merge(Ticker(symbol=sym, short_name=short, name=full, sector=SECTOR_VI.get(en, en), sector_en=en,
                       exchange=EXCHANGE.get(sym, "HOSE"), sort_order=i))
    s.flush()
    return len(art.tickers)


def upsert_prices(s: Session, df: pd.DataFrame) -> int:
    n = 0
    for r in df.itertuples(index=False):
        s.merge(Price(ticker=r.ticker, date=r.date, open=float(r.open), high=float(r.high), low=float(r.low),
                      close=float(r.close), volume=float(r.volume)))
        n += 1
    s.flush()
    return n


def upsert_index(s: Session, code: str, df: pd.DataFrame) -> int:
    for r in df.itertuples(index=False):
        s.merge(IndexPrice(code=code, date=r.date, open=float(r.open), high=float(r.high), low=float(r.low),
                           close=float(r.close), volume=float(r.volume)))
    s.flush()
    return len(df)


def last_price_date(s: Session, ticker: str | None = None) -> date | None:
    q = select(func.max(Price.date))
    if ticker:
        q = q.where(Price.ticker == ticker)
    return s.scalar(q)


def load_prices(s: Session, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    q = select(Price.ticker, Price.date, Price.open, Price.high, Price.low, Price.close, Price.volume)
    if start:
        q = q.where(Price.date >= start)
    if end:
        q = q.where(Price.date <= end)
    rows = s.execute(q).all()
    return pd.DataFrame(rows, columns=["ticker", "date", "open", "high", "low", "close", "volume"])


def trading_dates(s: Session, start: date | None = None, end: date | None = None) -> list[date]:
    q = select(Price.date).distinct()
    if start:
        q = q.where(Price.date >= start)
    if end:
        q = q.where(Price.date <= end)
    return sorted(s.scalars(q).all())


def emb_to_bytes(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def bytes_to_emb(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)


def add_news(s: Session, ticker: str, title: str, url: str, published_at: datetime, source: str = "CafeF") -> bool:
    exists = s.scalar(select(News.id).where(News.ticker == ticker, News.url == url))
    if exists:
        return False
    s.add(News(ticker=ticker, date=published_at.date(), published_at=published_at, title=title, url=url, source=source))
    return True


def log_start(s: Session, job: str) -> PipelineLog:
    entry = PipelineLog(job=job, status="running", started_at=datetime.now())
    s.add(entry)
    s.flush()
    return entry


def log_finish(s: Session, entry: PipelineLog, status: str, message: str | None = None) -> None:
    entry.status = status
    entry.message = message
    entry.finished_at = datetime.now()
    s.flush()


def clear_predictions(s: Session, as_of: date) -> None:
    from ..models import Explanation, Prediction, PredictionRun

    for model in (Prediction, Explanation, PredictionRun):
        s.execute(delete(model).where(model.as_of == as_of))
