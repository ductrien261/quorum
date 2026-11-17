"""Gemini tool-calling loop, streamed to the browser as server-sent events.

Events (JSON, one per ``data:`` line):
    {"type": "status", "text": "..."}       a tool is running
    {"type": "delta", "text": "..."}        a piece of the answer
    {"type": "tickers", "symbols": [...]}    tickers to show as cards under the answer
    {"type": "done"} | {"type": "error", "message": "..."}
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from typing import Any, Protocol

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import User
from .prompts import SYSTEM_PROMPT, context_note
from .tools import TOOLS, run_tool, tickers_in

log = logging.getLogger(__name__)

TOOL_STATUS = {
    "get_ai_picks": "Đang lấy danh sách gợi ý",
    "get_stock": "Đang tra cứu mã",
    "get_price_history": "Đang lấy lịch sử giá",
    "get_rank_history": "Đang lấy lịch sử hạng",
    "get_news": "Đang đọc tin tức",
    "compare_stocks": "Đang so sánh các mã",
    "screen_stocks": "Đang lọc cổ phiếu",
    "get_market_overview": "Đang xem tổng quan thị trường",
    "get_ai_track_record": "Đang tính hiệu quả gợi ý",
    "get_model_info": "Đang đọc thông tin mô hình",
    "get_my_watchlist": "Đang mở danh sách theo dõi",
}


class LLMStream(Protocol):
    """Minimal interface so tests can replace Gemini."""

    def stream(self, history: list[Any]) -> Iterator[Any]: ...


class GeminiLLM:
    def __init__(self):
        from google import genai
        from google.genai import types

        st = get_settings()
        if not st.gemini_api_key:
            raise RuntimeError("Chưa cấu hình GEMINI_API_KEY trong file .env")
        self.types = types
        self.client = genai.Client(api_key=st.gemini_api_key)
        self.model = st.gemini_model
        self.config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[
                types.FunctionDeclaration(name=name, description=desc, parameters_json_schema=schema)
                for name, (_, desc, schema) in TOOLS.items()
            ])],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    def user(self, text: str):
        return self.types.Content(role="user", parts=[self.types.Part(text=text)])

    def model_content(self, text: str):
        return self.types.Content(role="model", parts=[self.types.Part(text=text)])

    def tool_results(self, results: list[tuple[str, dict]]):
        return self.types.Content(role="user", parts=[
            self.types.Part.from_function_response(name=n, response={"result": r}) for n, r in results
        ])

    def stream(self, history):
        """Yields ('text', str) and ('call', name, args); finally ('content', Content) with every part received."""
        parts = []
        for chunk in self.client.models.generate_content_stream(model=self.model, contents=history, config=self.config):
            for cand in chunk.candidates or []:
                for p in (cand.content.parts if cand.content and cand.content.parts else []):
                    parts.append(p)
                    if p.function_call:
                        yield ("call", p.function_call.name, dict(p.function_call.args or {}))
                    elif p.text and not p.thought:
                        yield ("text", p.text)
        yield ("content", self.types.Content(role="model", parts=parts))


SYMBOL_RE = re.compile(r"\b[A-Z]{3}\b")


def answer(
    s: Session, llm, question: str, past: list[tuple[str, str]], ctx: dict | None, user: User | None,
    known_symbols: set[str],
) -> Iterator[dict]:
    history = []
    for role, text in past:
        history.append(llm.user(text) if role == "user" else llm.model_content(text))
    history.append(llm.user(context_note(ctx) + question))

    symbols: set[str] = set()
    text_out: list[str] = []
    max_rounds = get_settings().chat_max_tool_rounds
    for _ in range(max_rounds + 1):
        calls: list[tuple[str, dict]] = []
        content = None
        for ev in llm.stream(history):
            if ev[0] == "text":
                text_out.append(ev[1])
                yield {"type": "delta", "text": ev[1]}
            elif ev[0] == "call":
                calls.append((ev[1], ev[2]))
                yield {"type": "status", "text": TOOL_STATUS.get(ev[1], "Đang tra cứu dữ liệu")}
            elif ev[0] == "content":
                content = ev[1]
        if content is not None:
            history.append(content)
        if not calls:
            break
        results = []
        for name, args in calls:
            res = run_tool(name, args, s, user)
            symbols |= tickers_in(res) & known_symbols
            results.append((name, res))
        history.append(llm.tool_results(results))
    full = "".join(text_out)
    mentioned = {m for m in SYMBOL_RE.findall(full) if m in known_symbols}
    shown = [x for x in sorted(mentioned) if x in symbols or x in known_symbols][:6]
    if shown:
        yield {"type": "tickers", "symbols": shown}
    yield {"type": "final", "text": full, "symbols": shown}


def sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
