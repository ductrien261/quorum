"""Tools the assistant can call. Each tool reads the same service layer as the REST API,
so every number in an answer comes from the database."""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from sqlalchemy.orm import Session

from ..models import User
from ..services import market, performance, picks, screener, stocks
from ..services.common import NotFound

STATIC_MODEL_INFO = {
    "ten_mo_hinh": "MIDMoE (MarketMoE): xếp hạng cổ phiếu cho phiên kế tiếp",
    "cach_hoat_dong": (
        "Mỗi tối sau phiên, mô hình đọc 16 phiên gần nhất của 78 mã (7 chỉ báo kỹ thuật), tin tức CafeF gần nhất "
        "và quan hệ cùng ngành, rồi chấm điểm từng mã. 10 bản mô hình (10 seed) chấm độc lập; thứ hạng cuối là "
        "trung bình thứ hạng của 10 bản. 'Phiếu' = số bản xếp mã vào top 5."
    ),
    "du_lieu_huan_luyen": "Huấn luyện trên thị trường Mỹ 2015-2017, chuyển giao sang 78 mã Việt Nam với dữ liệu 2022-2024.",
    "ket_qua_kiem_dinh": (
        "Trên dữ liệu kiểm tra năm 2025 (chưa từng thấy khi huấn luyện), Sharpe theo ngày của top 5 khoảng 0,04, "
        "nhỉnh hơn chọn ngẫu nhiên (~0,033) nhưng chưa khác biệt có ý nghĩa thống kê."
    ),
    "han_che": [
        "Chưa tính phí giao dịch, thuế và trượt giá.",
        "Chưa mô hình hoá quy tắc T+2 và biên độ trần/sàn.",
        "Chỉ có điểm cho 78 mã trong rổ.",
        "Chuẩn hoá dữ liệu cố định theo giai đoạn 2022-2024, hiệu quả có thể giảm khi thị trường thay đổi.",
    ],
}


def _d(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


def _trim_pick(r: dict) -> dict:
    keep = ("symbol", "short_name", "sector", "rank", "votes", "rank_change", "close", "change_pct", "summary",
            "driver_label", "has_news", "realized_return")
    return {k: r.get(k) for k in keep}


def t_get_ai_picks(s: Session, date: str | None = None, k: int = 5, **_) -> dict:
    r = picks.picks(s, _d(date), max(1, min(int(k), 20)))
    return {"du_lieu_phien": r["as_of"], "ap_dung_cho_phien": r["target_session"], "so_mo_hinh": r["seeds"],
            "top": [_trim_pick(x) for x in r["rows"]], "tang_hang_manh": [_trim_pick(x) for x in r["movers"][:3]]}


def t_get_stock(s: Session, symbol: str, **_) -> dict:
    d = stocks.detail(s, symbol)
    try:
        e = stocks.explanation(s, symbol)
        d["giai_thich"] = {k: e[k] for k in ("summary", "sources", "features", "sector", "news", "votes", "seeds", "rank")}
    except NotFound:
        pass
    return d


def t_get_price_history(s: Session, symbol: str, days: int = 20, **_) -> dict:
    rows = stocks.prices(s, symbol, max(5, min(int(days), 120)))
    return {"symbol": symbol.upper(), "rows": [{k: r[k] for k in ("date", "close", "volume", "rsi", "macd")} for r in rows]}


def t_get_rank_history(s: Session, symbol: str, days: int = 20, **_) -> dict:
    return {"symbol": symbol.upper(), "rows": stocks.rank_history(s, symbol, max(5, min(int(days), 120)))}


def t_get_news(s: Session, symbol: str, days: int = 14, **_) -> dict:
    return {"symbol": symbol.upper(), "news": stocks.news(s, symbol, int(days), 10)}


def t_compare(s: Session, symbols: list[str], **_) -> dict:
    out = []
    for sym in symbols[:4]:
        try:
            d = stocks.detail(s, sym)
            out.append({"symbol": d["symbol"], "short_name": d["short_name"], "sector": d["sector"],
                        "price": d["price"], "ai": d["ai"]})
        except NotFound as e:
            out.append({"symbol": sym.upper(), "loi": str(e)})
    return {"so_sanh": out}


def t_screen(s: Session, **kw) -> dict:
    allowed = {k: kw[k] for k in ("sectors", "max_rank", "min_votes", "rsi_min", "rsi_max", "change_min", "change_max",
                                   "min_value_bn", "macd_positive", "sort") if k in kw and kw[k] is not None}
    r = screener.screen(s, screener.Filters(**allowed, limit=15))
    keep = ("symbol", "short_name", "sector", "close", "change_pct", "ai_rank", "ai_votes", "rsi", "ret_5d")
    return {"so_ma_khop": r["count"], "ket_qua": [{k: x.get(k) for k in keep} for x in r["rows"]]}


def t_market(s: Session, **_) -> dict:
    o = market.overview(s)
    return {"ngay": o["date"], "vnindex": {k: o["index"][k] for k in ("close", "change", "change_pct")},
            "do_rong": o["breadth"],
            "nganh": [{k: x[k] for k in ("sector", "avg_change_pct", "avg_ai_rank")} for x in o["sectors"]],
            "tang_manh": o["gainers"][:5], "giam_manh": o["losers"][:5]}


def t_track_record(s: Session, period: str = "all", k: int = 5, **_) -> dict:
    kind = {"2025": "history", "live": "live"}.get(period)
    r = performance.track_record(s, k=int(k), kind=kind)
    r.pop("daily", None)
    return r


def t_model_info(s: Session, **_) -> dict:
    return STATIC_MODEL_INFO


def t_my_watchlist(s: Session, user: User | None = None, **_) -> dict:
    if not user:
        return {"loi": "Người dùng chưa đăng nhập nên chưa có danh sách theo dõi."}
    from sqlalchemy import select

    from ..models import WatchItem

    syms = [w.ticker for w in s.scalars(select(WatchItem).where(WatchItem.user_id == user.id)).all()]
    rows = {r["symbol"]: r for r in market.board(s)["rows"]}
    keep = ("symbol", "short_name", "close", "change_pct", "ai_rank", "ai_votes", "ai_rank_change")
    return {"theo_doi": [{k: rows[x].get(k) for k in keep} for x in syms if x in rows]}


S = {"type": "string"}
I = {"type": "integer"}
N = {"type": "number"}

TOOLS: dict[str, tuple[Callable[..., Any], str, dict]] = {
    "get_ai_picks": (t_get_ai_picks, "Danh sách mã được mô hình xếp hạng cao nhất cho phiên kế tiếp (mặc định ngày mới nhất).",
                     {"type": "object", "properties": {"date": {**S, "description": "YYYY-MM-DD, bỏ trống = mới nhất"},
                                                       "k": {**I, "description": "số mã, 1-20"}}}),
    "get_stock": (t_get_stock, "Thông tin một mã: giá mới nhất, hạng AI, số phiếu, lý do xếp hạng (đóng góp từng nguồn, chỉ báo, ngành, tin).",
                  {"type": "object", "properties": {"symbol": S}, "required": ["symbol"]}),
    "get_price_history": (t_get_price_history, "Giá đóng cửa, khối lượng, RSI, MACD các phiên gần đây của một mã.",
                          {"type": "object", "properties": {"symbol": S, "days": I}, "required": ["symbol"]}),
    "get_rank_history": (t_get_rank_history, "Lịch sử hạng AI của một mã và lợi suất thực tế phiên sau.",
                         {"type": "object", "properties": {"symbol": S, "days": I}, "required": ["symbol"]}),
    "get_news": (t_get_news, "Tin tức CafeF gần đây của một mã.",
                 {"type": "object", "properties": {"symbol": S, "days": I}, "required": ["symbol"]}),
    "compare_stocks": (t_compare, "So sánh 2-4 mã: giá, thay đổi, hạng AI, số phiếu.",
                       {"type": "object", "properties": {"symbols": {"type": "array", "items": S}}, "required": ["symbols"]}),
    "screen_stocks": (t_screen, "Lọc mã trong rổ 78 mã theo ngành, hạng AI, số phiếu, RSI, % thay đổi, giá trị giao dịch.",
                      {"type": "object", "properties": {
                          "sectors": {"type": "array", "items": S, "description": "tên ngành tiếng Việt, ví dụ 'Ngân hàng'"},
                          "max_rank": I, "min_votes": I, "rsi_min": N, "rsi_max": N,
                          "change_min": {**N, "description": "tỉ lệ, ví dụ 0.02 = +2%"}, "change_max": N,
                          "min_value_bn": {**N, "description": "giá trị giao dịch tối thiểu, tỷ đồng"},
                          "macd_positive": {"type": "boolean"},
                          "sort": {**S, "description": "ai_rank | change_pct | value | rsi"}}}),
    "get_market_overview": (t_market, "Tổng quan thị trường phiên mới nhất: VN-Index, độ rộng, ngành, mã tăng/giảm mạnh.",
                            {"type": "object", "properties": {}}),
    "get_ai_track_record": (t_track_record, "Hiệu quả lịch sử của gợi ý top-K so với cả rổ và VN-Index.",
                            {"type": "object", "properties": {"period": {**S, "description": "all | 2025 | live"}, "k": I}}),
    "get_model_info": (t_model_info, "Mô tả mô hình, dữ liệu, kết quả kiểm định và hạn chế.", {"type": "object", "properties": {}}),
    "get_my_watchlist": (t_my_watchlist, "Danh sách mã người dùng đang theo dõi, kèm giá và hạng AI.", {"type": "object", "properties": {}}),
}


def run_tool(name: str, args: dict, s: Session, user: User | None) -> dict:
    if name not in TOOLS:
        return {"loi": f"Không có công cụ {name}"}
    fn = TOOLS[name][0]
    try:
        return fn(s, user=user, **(args or {}))
    except NotFound as e:
        return {"loi": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"loi": f"Lỗi khi tra cứu: {e}"}


def tickers_in(result: Any) -> set[str]:
    """Collect ticker symbols mentioned in a tool result (for clickable cards in the UI)."""
    found: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("symbol"), str):
                found.add(x["symbol"].upper())
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(result)
    return found
