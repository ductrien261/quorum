"""Scheduled jobs (Asia/Ho_Chi_Minh):

* once at startup  catch up on prices/news and predict sessions missed while the app was off

* 16:30 Mon-Fri  full daily job (prices, news, model, realised returns)
* every 5 minutes 09:00-15:00 Mon-Fri  refresh today's bars for the price board
"""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import get_settings
from ..db import session_scope

log = logging.getLogger(__name__)


def daily_job() -> None:
    from .jobs import run_daily

    try:
        with session_scope() as s:
            log.info("daily: %s", run_daily(s))
    except Exception:  # noqa: BLE001
        log.exception("daily job failed")


def catch_up_job() -> None:
    from .jobs import catch_up

    try:
        with session_scope() as s:
            log.info("catch-up: %s", catch_up(s))
    except Exception:  # noqa: BLE001
        log.exception("catch-up job failed")


def intraday_job() -> None:
    from . import jobs

    try:
        with session_scope() as s:
            today = jobs.kbs.today_vn()
            jobs.update_prices(s, start=today - timedelta(days=3), end=today)
    except Exception:  # noqa: BLE001
        log.exception("intraday refresh failed")


def _add_jobs(sched) -> None:
    tz = get_settings().timezone
    sched.add_job(daily_job, CronTrigger(day_of_week="mon-fri", hour=16, minute=30, timezone=tz), id="daily",
                  misfire_grace_time=3600, coalesce=True)
    sched.add_job(intraday_job, CronTrigger(day_of_week="mon-fri", hour="9-14", minute="*/5", timezone=tz),
                  id="intraday", misfire_grace_time=120, coalesce=True)


def start_background() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone=get_settings().timezone)
    _add_jobs(sched)
    sched.add_job(catch_up_job, id="catch-up")  # once, right after startup, in the background
    sched.start()
    return sched


def run_forever() -> None:
    sched = BlockingScheduler(timezone=get_settings().timezone)
    _add_jobs(sched)
    sched.add_job(catch_up_job, id="catch-up")
    log.info("Scheduler đang chạy: 16:30 T2-T6 và cập nhật giá 5 phút/lần trong phiên. Ctrl+C để dừng.")
    sched.start()
