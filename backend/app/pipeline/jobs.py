"""Pipeline jobs: fetch prices and news, run the model, store picks and explanations."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from functools import lru_cache

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..ml.artifacts import Artifacts, get_artifacts
from ..ml.cube import MarketImage, build_market_image, day_input
from ..ml.explain import explain_all, run_ablations
from ..ml.news import EMB_DIM, PhoBERTEmbedder, pick_news
from ..ml.predictor import Predictor
from ..models import News, Prediction, PredictionRun, Price
from ..reference import INDEX_CODE
from ..sources import cafef, kbs
from . import store

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    return Predictor(get_artifacts(get_settings().artifact_dir))


@lru_cache(maxsize=1)
def get_embedder() -> PhoBERTEmbedder:
    return PhoBERTEmbedder()


def artifacts() -> Artifacts:
    return get_artifacts(get_settings().artifact_dir)


# ---------------------------------------------------------------- prices


def update_prices(s: Session, start: date | None = None, end: date | None = None) -> int:
    """Fetch daily bars for the 78 tickers and VN-Index, incrementally from what is already stored."""
    art = artifacts()
    end = end or kbs.today_vn()
    default_start = date.fromisoformat(get_settings().price_history_start)
    n = 0
    for sym in art.tickers:
        last = store.last_price_date(s, sym)
        frm = start or (last - timedelta(days=7) if last else default_start)
        try:
            df = kbs.fetch_daily(sym, frm, end)
        except kbs.SourceError as e:
            log.error("Không lấy được giá %s: %s", sym, e)
            continue
        n += store.upsert_prices(s, df.assign(ticker=sym))
        s.commit()
    try:
        last_idx = s.scalar(select(Price.date).order_by(Price.date.desc()).limit(1))
        frm = start or default_start
        idx = kbs.fetch_daily(INDEX_CODE, frm, end, is_index=True)
        store.upsert_index(s, INDEX_CODE, idx)
        s.commit()
        log.info("VN-Index: %s phiên (đến %s)", len(idx), last_idx)
    except kbs.SourceError as e:
        log.error("Không lấy được VN-Index: %s", e)
    return n


# ---------------------------------------------------------------- news


def update_news(s: Session, since: date, until: date | None = None, embed: bool = True) -> int:
    art = artifacts()
    until = until or kbs.today_vn()
    added = 0
    for sym in art.tickers:
        known = {u: p for u, p in s.execute(select(News.url, News.published_at).where(News.ticker == sym)).all() if p}
        try:
            articles = cafef.crawl_ticker(sym, since, until, known_urls=set(known), known_dates=known)
        except Exception as e:  # noqa: BLE001
            log.error("CafeF %s lỗi: %s", sym, e)
            continue
        for a in articles:
            added += store.add_news(s, sym, a.title, a.url, a.published_at)
        s.commit()
        log.info("%s: +%s tin", sym, len(articles))
    if embed:
        embed_pending(s)
    return added


def embed_pending(s: Session, batch: int = 256) -> int:
    pending = s.scalars(select(News).where(News.embedding.is_(None))).all()
    if not pending:
        return 0
    emb = get_embedder()
    for i in range(0, len(pending), batch):
        chunk = pending[i : i + batch]
        vecs = emb.encode([n.title for n in chunk])
        for n, v in zip(chunk, vecs):
            n.embedding = store.emb_to_bytes(v)
        s.commit()
    return len(pending)


def news_inputs(s: Session, art: Artifacts, as_of: date) -> tuple[np.ndarray, np.ndarray, dict[str, dict]]:
    lower = as_of - timedelta(days=5)
    rows = s.scalars(
        select(News).where(News.date >= lower, News.date <= as_of, News.embedding.is_not(None))
    ).all()
    by_ticker: dict[str, list[News]] = {}
    for n in rows:
        by_ticker.setdefault(n.ticker, []).append(n)
    emb = np.zeros((1, art.n_stocks, EMB_DIM), dtype=np.float32)
    mask = np.zeros((1, art.n_stocks), dtype=np.float32)
    used: dict[str, dict] = {}
    for j, sym in enumerate(art.tickers):
        items = by_ticker.get(sym, [])
        nid = pick_news([(n.date, n.id) for n in items], as_of)
        if nid is None:
            continue
        n = next(x for x in items if x.id == nid)
        emb[0, j] = store.bytes_to_emb(n.embedding)
        mask[0, j] = 1.0
        used[sym] = {"date": n.date.isoformat(), "title": n.title, "url": n.url}
    return emb, mask, used


# ---------------------------------------------------------------- model


def predict_day(s: Session, as_of: date, img: MarketImage | None = None, kind: str = "live") -> PredictionRun:
    art = artifacts()
    pred = get_predictor()
    if img is None:
        start = as_of - timedelta(days=500)
        img = build_market_image(store.load_prices(s, start, as_of), art)
    di = day_input(img, as_of, art)
    news_emb, news_mask, used = news_inputs(s, art, as_of)
    abl = run_ablations(pred, di.x, news_emb, news_mask)
    payloads = explain_all(abl, art.tickers, _sector_vi(art), art.feature_order, di.raw_last, used)
    res = abl.full

    store.clear_predictions(s, as_of)
    run = PredictionRun(as_of=as_of, kind=kind, n_news=int(news_mask.sum()), filled=di.filled_tickers)
    s.add(run)
    from ..models import Explanation

    for j, sym in enumerate(art.tickers):
        s.add(Prediction(as_of=as_of, ticker=sym, rank=int(res.rank[j]), avg_rank=float(res.avg_rank[j]),
                         score=float(res.score[j]), score_std=float(res.score_std[j]), votes=int(res.votes[j]),
                         per_seed=[float(v) for v in res.per_seed[:, j]]))
        s.add(Explanation(as_of=as_of, ticker=sym, payload=payloads[sym]))
    s.flush()
    return run


def _sector_vi(art: Artifacts) -> dict[str, str]:
    from ..reference import SECTOR_VI

    return {k: SECTOR_VI.get(v, v) for k, v in art.sector_of().items()}


CLOSE_TIME = (15, 5)  # HOSE closes at 15:00; bars after 15:05 are final


def session_closed(d: date) -> bool:
    """False while ``d`` is today's session and the market has not closed yet (bar still moving)."""
    now = now_vn()
    if d < now.date():
        return True
    return d == now.date() and (now.hour, now.minute) >= CLOSE_TIME


def fill_realized(s: Session) -> int:
    """Set realized_return = next session close / as_of close - 1 where both closes are final."""
    pending = s.scalars(select(Prediction).where(Prediction.realized_return.is_(None))).all()
    if not pending:
        return 0
    dates = store.trading_dates(s)
    nxt = {d: dates[i + 1] for i, d in enumerate(dates[:-1])}
    closes = {(t, d): c for t, d, c in s.execute(select(Price.ticker, Price.date, Price.close)).all()}
    n = 0
    for p in pending:
        d1 = nxt.get(p.as_of)
        if d1 is None or not session_closed(d1):
            continue
        c0, c1 = closes.get((p.ticker, p.as_of)), closes.get((p.ticker, d1)) if d1 else None
        if c0 and c1:
            p.realized_return = c1 / c0 - 1
            n += 1
    s.flush()
    return n


def run_daily(s: Session, fetch: bool = True) -> dict:
    """The 16:30 job: refresh data, predict for the latest session, fill realised returns."""
    entry = store.log_start(s, "daily")
    s.commit()
    try:
        if fetch:
            update_prices(s)
            if get_settings().news_enabled:
                try:
                    update_news(s, since=kbs.today_vn() - timedelta(days=7))
                except Exception as e:  # noqa: BLE001
                    log.error("Bỏ qua tin tức: %s", e)
        as_of = store.last_price_date(s)
        if as_of is None:
            raise RuntimeError("Chưa có dữ liệu giá")
        if not session_closed(as_of):  # run during trading hours: use the last closed session
            dates = store.trading_dates(s)
            as_of = dates[-2] if len(dates) > 1 else as_of
        run = predict_day(s, as_of)
        filled = fill_realized(s)
        status = "degraded" if run.filled else "success"
        msg = f"Dự báo cho dữ liệu phiên {as_of}, {run.n_news} mã có tin, cập nhật {filled} lợi suất thực tế"
        store.log_finish(s, entry, status, msg)
        s.commit()
        return {"as_of": as_of.isoformat(), "status": status, "message": msg}
    except Exception as e:  # noqa: BLE001
        s.rollback()
        store.log_finish(s, entry, "failed", str(e))
        s.commit()
        raise


def catch_up(s: Session, max_news_days: int = 14) -> dict:
    """Run at startup: fetch what was missed while the app was off and predict every missed session."""
    last_run = s.scalar(select(PredictionRun.as_of).order_by(PredictionRun.as_of.desc()).limit(1))
    if last_run is None:  # fresh database: first-run.ps1 / the CLI does the initial load, not this job
        log.info("catch-up: chưa có dự báo nào, bỏ qua (hãy chạy first-run hoặc seed-history + backfill)")
        return {"sessions": 0, "message": "Bỏ qua: cơ sở dữ liệu còn trống"}
    entry = store.log_start(s, "catch-up")
    s.commit()
    try:
        update_prices(s)
        if get_settings().news_enabled:
            since = max(last_run - timedelta(days=5), kbs.today_vn() - timedelta(days=max_news_days))
            try:
                update_news(s, since=since)
            except Exception as e:  # noqa: BLE001
                log.error("Bỏ qua tin tức: %s", e)
        closed = [d for d in store.trading_dates(s) if session_closed(d)]
        missing = [d for d in closed if d > last_run]
        n = backfill(s, missing[0], missing[-1]) if missing else 0
        filled = fill_realized(s)
        s.commit()
        msg = f"Bù {n} phiên còn thiếu, cập nhật {filled} lợi suất thực tế"
        store.log_finish(s, entry, "success", msg)
        s.commit()
        return {"sessions": n, "message": msg}
    except Exception as e:  # noqa: BLE001
        s.rollback()
        store.log_finish(s, entry, "failed", str(e))
        s.commit()
        raise


def backfill(s: Session, start: date, end: date, kind: str = "live") -> int:
    art = artifacts()
    img = build_market_image(store.load_prices(s, start - timedelta(days=500), end), art)
    days = [d for d in img.dates if start <= d <= end and session_closed(d)]
    for i, d in enumerate(days):
        try:
            predict_day(s, d, img=img, kind=kind)
            s.commit()
        except ValueError as e:
            log.warning("Bỏ qua %s: %s", d, e)
        if i % 20 == 0:
            log.info("backfill %s/%s (%s)", i + 1, len(days), d)
    fill_realized(s)
    s.commit()
    return len(days)


def now_vn() -> datetime:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(get_settings().timezone))
