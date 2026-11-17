"""POST /api/chat — streamed assistant answers (SSE)."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from .assistant.agent import GeminiLLM, answer, sse
from .auth import optional_user
from .config import get_settings
from .db import SessionLocal
from .models import ChatMessage, Ticker, User

router = APIRouter(prefix="/api")
_hits: dict[str, deque] = defaultdict(deque)
_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = GeminiLLM()
    return _llm


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    context: dict | None = None


def _rate_ok(key: str) -> bool:
    now, limit = time.time(), get_settings().chat_rate_limit_per_hour
    q = _hits[key]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


@router.post("/chat")
def chat(body: ChatIn, request: Request, user: User | None = Depends(optional_user)):
    key = f"u{user.id}" if user else (request.client.host if request.client else "anon")
    if not _rate_ok(key):
        raise HTTPException(429, "Bạn đã hỏi quá nhiều trong một giờ. Vui lòng thử lại sau.")
    session_id = body.session_id or uuid.uuid4().hex
    try:
        llm = get_llm()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"Trợ lý chưa sẵn sàng: {e}") from e

    def gen():
        s = SessionLocal()
        try:
            yield sse({"type": "session", "session_id": session_id})
            turns = get_settings().chat_history_turns * 2
            past_rows = s.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id)
                                  .order_by(ChatMessage.id.desc()).limit(turns)).all()
            past = [(m.role, m.content) for m in reversed(past_rows)]
            known = set(s.scalars(select(Ticker.symbol)).all())
            final = None
            try:
                for ev in answer(s, llm, body.message, past, body.context, user, known):
                    if ev["type"] == "final":
                        final = ev
                        continue
                    yield sse(ev)
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    msg = "Hết hạn mức gọi Gemini. Đợi một lúc rồi hỏi lại, hoặc kiểm tra gói của API key."
                yield sse({"type": "error", "message": msg})
                return
            if final:
                s.add(ChatMessage(session_id=session_id, user_id=user.id if user else None, role="user", content=body.message))
                s.add(ChatMessage(session_id=session_id, user_id=user.id if user else None, role="assistant",
                                  content=final["text"], tickers=final["symbols"]))
                s.commit()
            yield sse({"type": "done"})
        finally:
            s.close()

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
