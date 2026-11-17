"""Command line entry point: ``python -m app.cli <command>`` (run from the backend/ folder).

    init                     create tables and the 78 tickers
    seed-history [--limit N] 2025 out-of-sample picks from the Kaggle test cube
    prices [--from DATE]     fetch daily bars (KBS) for the 78 tickers + VN-Index
    news --from DATE         crawl CafeF titles and embed them with PhoBERT
    backfill --from DATE [--to DATE]   run the model for every session in the range
    daily                    the scheduled job: refresh data and predict the latest session
    catch-up                 fetch what was missed and predict every missing session
    scheduler                run the 16:30 job (Mon-Fri) in the foreground
    demo                     load synthetic prices + predictions (offline development only)
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta

from .db import init_db, session_scope
from .ml.artifacts import get_artifacts
from .config import get_settings


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sh = sub.add_parser("seed-history")
    sh.add_argument("--limit", type=int, default=None)
    pr = sub.add_parser("prices")
    pr.add_argument("--from", dest="start", type=date.fromisoformat, default=None)
    nw = sub.add_parser("news")
    nw.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    nw.add_argument("--no-embed", action="store_true")
    bf = sub.add_parser("backfill")
    bf.add_argument("--from", dest="start", type=date.fromisoformat, required=True)
    bf.add_argument("--to", dest="end", type=date.fromisoformat, default=None)
    sub.add_parser("catch-up")
    dl = sub.add_parser("daily")
    dl.add_argument("--no-fetch", action="store_true")
    sub.add_parser("scheduler")
    dm = sub.add_parser("demo")
    dm.add_argument("--from", dest="start", type=date.fromisoformat, default=date(2024, 6, 3))
    dm.add_argument("--predict-from", type=date.fromisoformat, default=None)
    args = p.parse_args(argv)

    init_db()
    from .pipeline import jobs, store

    with session_scope() as s:
        store.seed_tickers(s, get_artifacts(get_settings().artifact_dir))

    if args.cmd == "init":
        print("Đã tạo cơ sở dữ liệu và 78 mã.")
    elif args.cmd == "seed-history":
        from .pipeline.history import seed_history

        with session_scope() as s:
            n = seed_history(s, args.limit)
        print(f"Đã nạp {n} phiên lịch sử 2025.")
    elif args.cmd == "prices":
        with session_scope() as s:
            n = jobs.update_prices(s, start=args.start)
            jobs.fill_realized(s)
        print(f"Đã cập nhật {n} dòng giá.")
    elif args.cmd == "news":
        with session_scope() as s:
            n = jobs.update_news(s, since=args.start, embed=not args.no_embed)
        print(f"Đã thêm {n} tin.")
    elif args.cmd == "backfill":
        with session_scope() as s:
            n = jobs.backfill(s, args.start, args.end or jobs.kbs.today_vn())
        print(f"Đã chạy mô hình cho {n} phiên.")
    elif args.cmd == "catch-up":
        with session_scope() as s:
            print(jobs.catch_up(s))
    elif args.cmd == "daily":
        with session_scope() as s:
            print(jobs.run_daily(s, fetch=not args.no_fetch))
    elif args.cmd == "scheduler":
        from .pipeline.scheduler import run_forever

        run_forever()
    elif args.cmd == "demo":
        from .pipeline.demo import load_demo

        end = jobs.kbs.today_vn() - timedelta(days=1)
        with session_scope() as s:
            load_demo(s, args.start, end)
            start = args.predict_from or (end - timedelta(days=150))
            n = jobs.backfill(s, start, end)
        print(f"Đã nạp dữ liệu giả lập và chạy mô hình cho {n} phiên.")


if __name__ == "__main__":
    main()
