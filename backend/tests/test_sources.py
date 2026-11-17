from datetime import date, datetime

from app.sources import cafef, kbs

SEARCH_HTML = """
<div class="item"><a class="box-category-link-title" href="/hpg-lai-ky-luc-188.chn">HPG lãi kỷ lục</a></div>
<div class="item"><a class="box-category-link-title" href="/thep-tang-gia-189.chn">Giá thép tăng</a></div>
<div class="item"><span>quảng cáo</span></div>
"""
ARTICLE = '<html><head><meta property="article:published_time" content="{}"/></head></html>'


def test_parse_search_page():
    items = cafef.parse_search_page(SEARCH_HTML)
    assert items == [
        ("HPG lãi kỷ lục", "https://cafef.vn/hpg-lai-ky-luc-188.chn"),
        ("Giá thép tăng", "https://cafef.vn/thep-tang-gia-189.chn"),
    ]


def test_parse_published_time():
    assert cafef.parse_published(ARTICLE.format("2026-03-26T08:06:00")) == datetime(2026, 3, 26, 8, 6)
    assert cafef.parse_published("<html></html>") is None


class _R:
    def __init__(self, text):
        self.text = text


def test_crawl_filters_dates_and_stops():
    pages = {
        cafef.search_url("HPG", 1): SEARCH_HTML,
        "https://cafef.vn/hpg-lai-ky-luc-188.chn": ARTICLE.format("2026-11-14T09:00:00"),
        "https://cafef.vn/thep-tang-gia-189.chn": ARTICLE.format("2024-01-02T09:00:00"),
    }
    got = cafef.crawl_ticker("HPG", date(2026, 11, 1), date(2026, 11, 16), get=lambda u: _R(pages.get(u, "")), delay=0)
    assert [a.title for a in got] == ["HPG lãi kỷ lục"]
    assert got[0].date == date(2026, 11, 14)


def test_kbs_parse_divides_stock_prices():
    payload = {"data_day": [
        {"t": "2026-11-13 07:00:00", "o": 26100, "h": 26500, "l": 25900, "c": 26400, "v": 12000000},
        {"t": "2026-11-14 07:00:00", "o": 26400, "h": 26800, "l": 26300, "c": 26700, "v": 9000000},
    ]}
    df = kbs.parse_bars(payload, divide=True)
    assert df["close"].tolist() == [26.4, 26.7]
    assert df["date"].tolist() == [date(2026, 11, 13), date(2026, 11, 14)]
    idx = kbs.parse_bars(payload, divide=False)
    assert idx["close"].iloc[0] == 26400
