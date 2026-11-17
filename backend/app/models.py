from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Ticker(Base):
    __tablename__ = "tickers"
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    short_name: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(80))  # Vietnamese
    sector_en: Mapped[str] = mapped_column(String(80))
    exchange: Mapped[str] = mapped_column(String(10), default="HOSE")
    sort_order: Mapped[int] = mapped_column(Integer)


class Price(Base):
    __tablename__ = "prices"
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0)


class IndexPrice(Base):
    __tablename__ = "index_prices"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0)


class News(Base):
    __tablename__ = "news"
    __table_args__ = (UniqueConstraint("ticker", "url", name="uq_news_ticker_url"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(600))
    source: Mapped[str] = mapped_column(String(40), default="CafeF")
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)


class PredictionRun(Base):
    __tablename__ = "prediction_runs"
    as_of: Mapped[date] = mapped_column(Date, primary_key=True)  # last session in the input window
    kind: Mapped[str] = mapped_column(String(16), default="live")  # history | live
    model_version: Mapped[str] = mapped_column(String(40), default="midmoe-vn-10seed")
    n_news: Mapped[int] = mapped_column(Integer, default=0)
    filled: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"
    as_of: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    rank: Mapped[int] = mapped_column(Integer)
    avg_rank: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    score_std: Mapped[float] = mapped_column(Float)
    votes: Mapped[int] = mapped_column(Integer)
    per_seed: Mapped[list] = mapped_column(JSON)
    realized_return: Mapped[float | None] = mapped_column(Float, nullable=True)  # next session close/close - 1


class Explanation(Base):
    __tablename__ = "explanations"
    as_of: Mapped[date] = mapped_column(Date, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16))  # running | success | degraded | failed | skipped
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WatchItem(Base):
    __tablename__ = "watchlist"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    tickers: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
