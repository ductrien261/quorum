import numpy as np
import pandas as pd

from app.ml.features import compute_indicators, normalize
from app.ml.news import pick_news
from app.ml.predictor import combine, per_seed_ranks

from .conftest import ARTIFACTS, needs_artifacts


def _ohlc(n=60, seed=0):
    rng = np.random.default_rng(seed)
    close = 20 * np.cumprod(1 + rng.normal(0, 0.02, n))
    return pd.DataFrame({
        "date": pd.bdate_range("2025-01-01", periods=n).date,
        "open": close * 0.99, "high": close * 1.01, "low": close * 0.98, "close": close,
    })


def test_indicator_warmup_matches_notebook():
    """The notebook printed 1 NaN for RSI, 25 for MACD, 10 for ret_10d (pandas-ta 0.4.x)."""
    df = compute_indicators(_ohlc())
    assert df["rsi"].isna().sum() == 1
    assert df["macd"].isna().sum() == 25
    assert df["ret_10d"].isna().sum() == 10
    assert df["close_open_ratio"].isna().sum() == 0


def test_rsi_bounds_and_direction():
    up = pd.DataFrame({"date": pd.bdate_range("2025-01-01", periods=40).date, "close": np.linspace(10, 20, 40)})
    up["open"] = up["high"] = up["low"] = up["close"]
    assert compute_indicators(up)["rsi"].iloc[-1] > 99


def test_normalize_clips_to_unit_interval():
    params = {"a": {"p1": -1, "p99": 1, "min": -1, "max": 1}}
    out = normalize(np.array([[-5.0], [0.0], [5.0]]), ["a"], params)
    assert np.allclose(out[:, 0], [0, 0.5, 1], atol=1e-6)


def test_pick_news_latest_within_five_days():
    from datetime import date

    items = [(date(2025, 3, 1), 1), (date(2025, 3, 6), 2), (date(2025, 3, 9), 3)]
    assert pick_news(items, date(2025, 3, 7)) == 2
    assert pick_news(items, date(2025, 3, 20)) is None
    assert pick_news(items, date(2025, 3, 9)) == 3


def test_ensemble_votes_and_ranks():
    scores = np.array([[3.0, 2.0, 1.0, 0.0, -1, -2], [2.0, 3.0, 1.0, 0.0, -1, -2]])
    r = per_seed_ranks(scores)
    assert r[0].tolist() == [1, 2, 3, 4, 5, 6]
    res = combine(scores)
    assert res.rank[:2].tolist() in ([1, 2], [2, 1])
    assert res.votes.tolist() == [2, 2, 2, 2, 2, 0]


@needs_artifacts
def test_parity_with_kaggle_reference():
    """The packaged model must reproduce the notebook's exported predictions exactly."""
    from app.ml.artifacts import load_artifacts
    from app.ml.predictor import Predictor

    art = load_artifacts(ARTIFACTS)
    pred = Predictor(art)
    ref = np.load(ARTIFACTS / "vn_parity_ref.npz", allow_pickle=True)["per_seed"]
    cube = np.load(ARTIFACTS / "vn_test_cube.npz", allow_pickle=True)
    for i in (0, 120, len(cube["x"]) - 1):
        s = pred.raw_scores(cube["x"][i : i + 1], cube["news_emb"][i : i + 1], cube["news_mask"][i : i + 1])
        assert np.abs(s - ref[:, i]).max() < 1e-4
