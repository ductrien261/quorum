"""Load the model artifacts exported from Kaggle (``midmoe-vn-transfer-weights``).

Expected layout of ``ARTIFACT_DIR``::

    model_config.json        hyper-parameters (N, T_WINDOW, D, F_dim, ...)
    vn_tickers_sorted.json   78 tickers, sorted by ICB sector (model input order)
    vn_feature_order.json    the 7 indicators, in input order
    vn_norm_params.json      winsorize + min-max parameters fitted on 2022-2024
    vn_sector_graph.npy      78 x 78 same-sector adjacency
    icb_industry.csv         symbol, sector, icb_code_lv2, icb_code_lv4
    weights/model_seed{0..9}.pt
    vn_parity_ref.npz        reference predictions on vn_test_cube.npz (tests only)
    vn_test_cube.npz         2025 test cube (tests and history seeding only)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Artifacts:
    root: Path
    config: dict
    tickers: list[str]
    feature_order: list[str]
    norm_params: dict[str, dict[str, float]]
    sector_graph: np.ndarray
    icb: pd.DataFrame

    @property
    def n_stocks(self) -> int:
        return len(self.tickers)

    @property
    def window(self) -> int:
        return int(self.config["T_WINDOW"])

    @property
    def noise_seed(self) -> int:
        return int(self.config.get("noise_seed", 0))

    def weight_files(self) -> list[Path]:
        files = sorted((self.root / "weights").glob("model_seed*.pt"), key=lambda p: int(p.stem.replace("model_seed", "")))
        if not files:
            raise FileNotFoundError(f"No weights found in {self.root / 'weights'}")
        return files

    def a_norm(self) -> np.ndarray:
        """SGC-style normalised adjacency, exactly as in the notebook (Phase 1)."""
        g = self.sector_graph.astype(np.float32)
        n = g.shape[0]
        a_hat = g + np.eye(n, dtype=np.float32) * (g.diagonal() == 0)
        deg = a_hat.sum(axis=1)
        deg_inv_sqrt = np.zeros_like(deg)
        np.power(deg, -0.5, out=deg_inv_sqrt, where=deg > 0)
        return (deg_inv_sqrt[:, None] * a_hat * deg_inv_sqrt[None, :]).astype(np.float32)

    def sector_of(self) -> dict[str, str]:
        return dict(zip(self.icb["symbol"], self.icb["sector"]))


def load_artifacts(root: str | Path) -> Artifacts:
    root = Path(root)
    if not (root / "model_config.json").exists():
        raise FileNotFoundError(
            f"Không tìm thấy artifacts trong '{root}'. Chép thư mục artifacts/vn từ Kaggle vào đây (xem README)."
        )
    config = json.loads((root / "model_config.json").read_text(encoding="utf-8"))
    tickers = json.loads((root / "vn_tickers_sorted.json").read_text(encoding="utf-8"))
    feature_order = json.loads((root / "vn_feature_order.json").read_text(encoding="utf-8"))
    norm_params = json.loads((root / "vn_norm_params.json").read_text(encoding="utf-8"))
    graph = np.load(root / "vn_sector_graph.npy")
    icb = pd.read_csv(root / "icb_industry.csv", dtype={"icb_code_lv2": str, "icb_code_lv4": str})
    if graph.shape != (len(tickers), len(tickers)):
        raise ValueError(f"sector graph {graph.shape} does not match {len(tickers)} tickers")
    return Artifacts(root, config, tickers, feature_order, norm_params, graph, icb)


@lru_cache(maxsize=4)
def get_artifacts(root: str) -> Artifacts:
    return load_artifacts(root)
