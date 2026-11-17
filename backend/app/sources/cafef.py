"""News titles from the CafeF search page, as in notebook ``midmoe-vn-data-prepare`` Phase 7.

* list:  https://cafef.vn/tim-kiem.chn?keywords=<TICKER>, then /tim-kiem/trang-<n>.chn?keywords=<TICKER>
* item:  ``div.item`` > ``a.box-category-link-title`` (title + relative href)
* date:  ``<meta property="article:published_time">`` of the article page;
         the calendar date of that timestamp is the news date.

Search results are not strictly date-ordered, so the crawl stops after
``max_empty_pages`` consecutive pages without any article in range.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE = "https://cafef.vn"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


@dataclass
class Article:
    ticker: str
    title: str
    url: str
    published_at: datetime

    @property
    def date(self) -> date:
        return self.published_at.date()


def search_url(ticker: str, page: int) -> str:
    if page == 1:
        return f"{BASE}/tim-kiem.chn?keywords={ticker}"
    return f"{BASE}/tim-kiem/trang-{page}.chn?keywords={ticker}"


def parse_search_page(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for it in soup.find_all("div", class_="item"):
        a = it.find("a", class_="box-category-link-title")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        url = href if href.startswith("http") else BASE + href
        out.append((a.get_text(strip=True), url))
    return out


def parse_published(html: str) -> datetime | None:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    if not meta or not meta.get("content"):
        return None
    try:
        return datetime.fromisoformat(meta["content"].replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def crawl_ticker(
    ticker: str,
    since: date,
    until: date,
    known_urls: set[str] | None = None,
    known_dates: dict[str, datetime] | None = None,
    max_pages: int = 30,
    max_empty_pages: int = 3,
    delay: float = 0.4,
    session: requests.Session | None = None,
    get: Callable | None = None,
) -> list[Article]:
    """Articles about ``ticker`` published in [since, until]."""
    s = session or requests.Session()
    fetch = get or (lambda url: s.get(url, headers=HEADERS, timeout=10))
    known_dates = known_dates or {}
    out: list[Article] = []
    empty = 0
    for page in range(1, max_pages + 1):
        try:
            r = fetch(search_url(ticker, page))
            items = parse_search_page(r.text)
        except Exception as e:  # noqa: BLE001
            log.warning("CafeF %s trang %s lỗi: %s", ticker, page, e)
            break
        if not items:
            break
        in_range = 0
        for title, url in items:
            pub = known_dates.get(url)
            if pub is None:
                try:
                    time.sleep(delay)
                    pub = parse_published(fetch(url).text)
                except Exception:  # noqa: BLE001
                    pub = None
            if pub is None or not (since <= pub.date() <= until):
                continue
            in_range += 1
            if known_urls and url in known_urls:
                continue
            out.append(Article(ticker, title, url, pub))
        empty = empty + 1 if in_range == 0 else 0
        if empty >= max_empty_pages:
            break
        time.sleep(delay)
    return out
