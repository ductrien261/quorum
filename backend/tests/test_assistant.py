"""The assistant loop with a scripted fake LLM (no network, no API key)."""

from app.assistant.agent import answer
from app.assistant.tools import TOOLS, run_tool, tickers_in


class FakeLLM:
    """Round 1: ask for the AI picks. Round 2: answer with the first pick's ticker."""

    def __init__(self):
        self.rounds = 0
        self.seen_results = None

    def user(self, text):
        return ("user", text)

    def model_content(self, text):
        return ("model", text)

    def tool_results(self, results):
        self.seen_results = results
        return ("tool", results)

    def stream(self, history):
        self.rounds += 1
        if self.rounds == 1:
            yield ("call", "get_ai_picks", {"k": 3})
            yield ("content", ("model", "call"))
        else:
            top = self.seen_results[0][1]["top"][0]["symbol"]
            yield ("text", f"Mã đứng đầu là {top}. ")
            yield ("text", "Đây là thông tin tham khảo.")
            yield ("content", ("model", "text"))


def test_tool_loop_uses_database(demo_db):
    from app.db import SessionLocal

    s = SessionLocal()
    llm = FakeLLM()
    events = list(answer(s, llm, "Top 3 hôm nay?", [], {"page": "Tổng quan"}, None, {"HPG", "FPT", "VCB", *TOOLS_SYMS(s)}))
    s.close()
    kinds = [e["type"] for e in events]
    assert kinds[0] == "status"
    assert "delta" in kinds and kinds[-1] == "final"
    final = events[-1]
    assert final["symbols"] and final["symbols"][0] in final["text"]


def TOOLS_SYMS(s):
    from sqlalchemy import select

    from app.models import Ticker

    return set(s.scalars(select(Ticker.symbol)).all())


def test_every_tool_runs(demo_db):
    from app.db import SessionLocal

    s = SessionLocal()
    args = {"get_stock": {"symbol": "FPT"}, "get_price_history": {"symbol": "FPT"}, "get_rank_history": {"symbol": "FPT"},
            "get_news": {"symbol": "FPT"}, "compare_stocks": {"symbols": ["FPT", "CMG"]}, "screen_stocks": {"max_rank": 10}}
    for name in TOOLS:
        res = run_tool(name, args.get(name, {}), s, None)
        assert isinstance(res, dict), name
        if name not in ("get_my_watchlist",):
            assert "loi" not in res or name == "get_news", (name, res)
    assert "FPT" in tickers_in(run_tool("get_stock", {"symbol": "fpt"}, s, None))
    assert "loi" in run_tool("get_stock", {"symbol": "ZZZ"}, s, None)
    s.close()
