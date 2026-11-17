"""REST endpoints (prefix /api)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import create_token, current_user, hash_password, verify_password
from .db import get_db
from .models import Prediction, User, WatchItem
from .services import market, performance, picks, screener, stocks, system
from .services.common import NotFound, resolve_as_of, ticker_or_404, tickers_map

router = APIRouter(prefix="/api")


def _nf(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {"ok": True, **system.status(db)}


@router.get("/tickers")
def tickers(db: Session = Depends(get_db)):
    return [{"symbol": t.symbol, "short_name": t.short_name, "name": t.name, "sector": t.sector, "exchange": t.exchange}
            for t in tickers_map(db).values()]


@router.get("/market/overview")
def market_overview(db: Session = Depends(get_db)):
    return _nf(market.overview, db)


@router.get("/market/board")
def price_board(date_: date | None = Query(None, alias="date"), db: Session = Depends(get_db)):
    return _nf(market.board, db, date_)


@router.get("/ai/dates")
def ai_dates(db: Session = Depends(get_db)):
    return picks.run_dates(db)


@router.get("/ai/picks")
def ai_picks(date_: date | None = Query(None, alias="date"), k: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    return _nf(picks.picks, db, date_, k)


@router.get("/ai/rankings")
def ai_rankings(date_: date | None = Query(None, alias="date"), db: Session = Depends(get_db)):
    return _nf(picks.rankings, db, date_)


@router.get("/ai/track-record")
def track_record(
    start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
    k: int = Query(5, ge=1, le=20), kind: str | None = None, db: Session = Depends(get_db),
):
    return performance.track_record(db, start, end, k, kind)


@router.get("/stocks/{symbol}")
def stock_detail(symbol: str, db: Session = Depends(get_db)):
    return _nf(stocks.detail, db, symbol)


@router.get("/stocks/{symbol}/prices")
def stock_prices(symbol: str, days: int = Query(250, ge=20, le=1000), db: Session = Depends(get_db)):
    return _nf(stocks.prices, db, symbol, days)


@router.get("/stocks/{symbol}/rank-history")
def stock_rank_history(symbol: str, days: int = Query(120, ge=5, le=500), db: Session = Depends(get_db)):
    return _nf(stocks.rank_history, db, symbol, days)


@router.get("/stocks/{symbol}/explanation")
def stock_explanation(symbol: str, date_: date | None = Query(None, alias="date"), db: Session = Depends(get_db)):
    return _nf(stocks.explanation, db, symbol, date_)


@router.get("/stocks/{symbol}/news")
def stock_news(symbol: str, days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    return _nf(stocks.news, db, symbol, days)


@router.get("/stocks/{symbol}/peers")
def stock_peers(symbol: str, db: Session = Depends(get_db)):
    return _nf(stocks.peers, db, symbol)


@router.get("/screener")
def screen(
    sectors: list[str] | None = Query(None), max_rank: int | None = None, min_votes: int | None = None,
    rsi_min: float | None = None, rsi_max: float | None = None, change_min: float | None = None,
    change_max: float | None = None, ret5_min: float | None = None, ret5_max: float | None = None,
    min_value_bn: float | None = None, macd_positive: bool | None = None, sort: str = "ai_rank",
    db: Session = Depends(get_db),
):
    f = screener.Filters(sectors, max_rank, min_votes, rsi_min, rsi_max, change_min, change_max, ret5_min, ret5_max,
                         min_value_bn, macd_positive, sort)
    return _nf(screener.screen, db, f)


# ------------------------------------------------------------------ auth + watchlist


class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _user_out(u: User, token: str | None = None) -> dict:
    out = {"id": u.id, "email": u.email, "name": u.name}
    return {"user": out, "token": token} if token else out


@router.post("/auth/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email này đã có tài khoản. Hãy đăng nhập.")
    u = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    return _user_out(u, create_token(u.id))


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
    return _user_out(u, create_token(u.id))


@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return _user_out(user)


@router.get("/watchlist")
def get_watchlist(user: User = Depends(current_user), db: Session = Depends(get_db)):
    items = db.scalars(select(WatchItem).where(WatchItem.user_id == user.id).order_by(WatchItem.added_at)).all()
    syms = [i.ticker for i in items]
    board = {r["symbol"]: r for r in market.board(db)["rows"]} if syms else {}
    return {"symbols": syms, "rows": [board[s] for s in syms if s in board]}


@router.put("/watchlist/{symbol}")
def add_watch(symbol: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _nf(ticker_or_404, db, symbol)
    if not db.get(WatchItem, (user.id, t.symbol)):
        db.add(WatchItem(user_id=user.id, ticker=t.symbol))
        db.commit()
    return {"ok": True}


@router.delete("/watchlist/{symbol}")
def remove_watch(symbol: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.get(WatchItem, (user.id, symbol.upper()))
    if item:
        db.delete(item)
        db.commit()
    return {"ok": True}


@router.get("/search")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    ql = q.strip().lower()
    try:
        d = resolve_as_of(db)
        ranks = {p.ticker: p.rank for p in db.scalars(select(Prediction).where(Prediction.as_of == d)).all()}
    except NotFound:
        ranks = {}
    hits = [t for t in tickers_map(db).values()
            if t.symbol.lower().startswith(ql) or ql in t.short_name.lower() or ql in t.name.lower()]
    hits.sort(key=lambda t: (not t.symbol.lower().startswith(ql), t.symbol))
    return [{"symbol": t.symbol, "short_name": t.short_name, "sector": t.sector, "ai_rank": ranks.get(t.symbol)}
            for t in hits[:8]]
