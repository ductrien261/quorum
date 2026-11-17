"""FastAPI application: ``uvicorn app.main:app --reload`` from the backend/ folder."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .chat import router as chat_router
from .config import get_settings
from .db import init_db, session_scope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    try:
        from .ml.artifacts import get_artifacts
        from .pipeline.store import seed_tickers

        with session_scope() as s:
            seed_tickers(s, get_artifacts(get_settings().artifact_dir))
    except FileNotFoundError as e:
        logging.getLogger(__name__).warning("%s", e)
    sched = None
    if get_settings().run_scheduler:
        from .pipeline.scheduler import start_background

        sched = start_background()
    yield
    if sched:
        sched.shutdown(wait=False)


app = FastAPI(title="Quorum API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(chat_router)
