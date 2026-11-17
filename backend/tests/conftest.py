import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "vn"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

needs_artifacts = pytest.mark.skipif(
    not (ARTIFACTS / "weights" / "model_seed0.pt").exists(), reason="artifacts/vn chưa có (xem README)"
)


@pytest.fixture(scope="session")
def demo_db(tmp_path_factory):
    """A database with 3 history days + ~2 weeks of synthetic prices and predictions."""
    if not (ARTIFACTS / "weights" / "model_seed0.pt").exists():
        pytest.skip("artifacts/vn chưa có")
    db = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    os.environ["ARTIFACT_DIR"] = str(ARTIFACTS)
    from app.config import get_settings

    get_settings.cache_clear()
    from app import cli

    cli.main(["init"])
    cli.main(["seed-history", "--limit", "3"])
    from datetime import date, timedelta

    from app.pipeline.jobs import kbs

    end = kbs.today_vn() - timedelta(days=1)
    cli.main(["demo", "--from", (end - timedelta(days=200)).isoformat(), "--predict-from", (end - timedelta(days=14)).isoformat()])
    return db
