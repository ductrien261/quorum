import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(demo_db):
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_read_endpoints(client):
    for path in [
        "/api/health", "/api/tickers", "/api/market/overview", "/api/market/board", "/api/ai/dates",
        "/api/ai/picks?k=5", "/api/ai/rankings", "/api/ai/track-record", "/api/stocks/FPT",
        "/api/stocks/FPT/prices?days=60", "/api/stocks/FPT/rank-history", "/api/stocks/FPT/explanation",
        "/api/stocks/FPT/news", "/api/stocks/FPT/peers", "/api/screener?max_rank=20", "/api/search?q=hoa",
    ]:
        r = client.get(path)
        assert r.status_code == 200, (path, r.text)


def test_picks_shape(client):
    d = client.get("/api/ai/picks?k=5").json()
    assert len(d["rows"]) == 5
    assert [r["rank"] for r in d["rows"]] == [1, 2, 3, 4, 5]
    assert all(0 <= r["votes"] <= d["seeds"] for r in d["rows"])


def test_rankings_cover_basket(client):
    rows = client.get("/api/ai/rankings").json()["rows"]
    assert len(rows) == 78
    assert sorted(r["rank"] for r in rows) == list(range(1, 79))


def test_history_has_realized_returns(client):
    tr = client.get("/api/ai/track-record?kind=history").json()
    assert tr["n_days"] == 3
    assert tr["top"]["total_return"] is not None


def test_unknown_ticker_is_404(client):
    assert client.get("/api/stocks/ZZZ").status_code == 404


def test_auth_and_watchlist(client):
    r = client.post("/api/auth/register", json={"email": "nha.dau.tu@example.com", "name": "Nhà đầu tư", "password": "matkhau1"})
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.post("/api/auth/register", json={"email": "nha.dau.tu@example.com", "name": "X", "password": "matkhau1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "nha.dau.tu@example.com", "password": "sai"}).status_code == 401
    assert client.get("/api/watchlist").status_code == 401
    client.put("/api/watchlist/HPG", headers=h)
    client.put("/api/watchlist/VCB", headers=h)
    assert client.get("/api/watchlist", headers=h).json()["symbols"] == ["HPG", "VCB"]
    client.delete("/api/watchlist/HPG", headers=h)
    assert client.get("/api/watchlist", headers=h).json()["symbols"] == ["VCB"]
