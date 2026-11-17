from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import News, PipelineLog, PredictionRun, Price


def status(s: Session) -> dict:
    last = s.scalars(select(PipelineLog).where(PipelineLog.job == "daily").order_by(PipelineLog.id.desc()).limit(1)).first()
    demo = s.scalar(select(func.count()).select_from(PipelineLog).where(PipelineLog.job == "demo-data")) > 0
    return {
        "latest_price_date": (d.isoformat() if (d := s.scalar(select(func.max(Price.date)))) else None),
        "latest_as_of": (d.isoformat() if (d := s.scalar(select(func.max(PredictionRun.as_of)))) else None),
        "n_runs": s.scalar(select(func.count()).select_from(PredictionRun)),
        "n_news": s.scalar(select(func.count()).select_from(News)),
        "demo_data": demo,
        "last_job": {
            "status": last.status, "message": last.message,
            "started_at": last.started_at.isoformat() if last.started_at else None,
            "finished_at": last.finished_at.isoformat() if last.finished_at else None,
        } if last else None,
    }
