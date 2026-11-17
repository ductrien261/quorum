"""Ensemble of the 10 exported MarketMoE seeds.

Each seed is run with ``seeded_forward``: the model adds a tiny amount of
diffusion noise even in eval mode (k = 0), so the noise RNG is fixed to the
same seed the notebook used when it wrote ``vn_parity_ref.npz``. With this the
web app reproduces the notebook's predictions exactly.

Ensemble rule: each seed ranks the 78 stocks; the final order is the average
rank across seeds (robust to seeds having different score scales). We also
keep the mean raw score, its spread, and ``votes`` = how many seeds put the
stock in their top 5 (the "quorum" shown in the UI).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch

from .artifacts import Artifacts
from .marketmoe import MarketMoE

TOP_K_VOTE = 5


@dataclass
class EnsembleResult:
    per_seed: np.ndarray  # (S, N) raw scores
    score: np.ndarray  # (N,) mean raw score
    score_std: np.ndarray  # (N,)
    avg_rank: np.ndarray  # (N,) mean of per-seed ranks (1 = best)
    rank: np.ndarray  # (N,) final rank, 1..N
    votes: np.ndarray  # (N,) seeds that put the stock in their top 5


def seeded_forward(model: MarketMoE, x, news_emb, news_mask, noise_seed: int = 0) -> torch.Tensor:
    """Must stay identical to the notebook's ``seeded_forward``."""
    with torch.random.fork_rng(devices=[]), torch.no_grad():
        torch.manual_seed(noise_seed)
        r_final, _, _ = model(x, news_emb, news_mask)
    return r_final


def build_model(art: Artifacts) -> MarketMoE:
    c = art.config
    return MarketMoE(
        N=art.n_stocks, T=art.window, D=int(c["D"]), news_emb_dim=int(c.get("news_emb_dim", c["EMB_DIM"])),
        A_norm=torch.from_numpy(art.a_norm()), market_conv_type=c.get("market_conv_type", "conv3d"),
        F_dim=int(c["F_dim"]), dit_dim=int(c["dit_dim"]), dit_heads=int(c["dit_heads"]),
        dit_blocks=int(c["dit_blocks"]), num_middle=int(c["num_middle"]), num_bottom=int(c["num_bottom"]),
        diffusion_K=int(c["diffusion_K"]),
    )


def per_seed_ranks(scores: np.ndarray) -> np.ndarray:
    """(S, N) scores -> (S, N) ranks, 1 = highest score."""
    order = np.argsort(-scores, axis=1, kind="stable")
    ranks = np.empty_like(order)
    rows = np.arange(scores.shape[0])[:, None]
    ranks[rows, order] = np.arange(1, scores.shape[1] + 1)[None, :]
    return ranks


def combine(per_seed: np.ndarray) -> EnsembleResult:
    ranks = per_seed_ranks(per_seed)
    avg_rank = ranks.mean(axis=0)
    score = per_seed.mean(axis=0)
    # final order: lower average rank first, ties broken by higher mean score
    order = np.lexsort((-score, avg_rank))
    final_rank = np.empty(per_seed.shape[1], dtype=int)
    final_rank[order] = np.arange(1, per_seed.shape[1] + 1)
    votes = (ranks <= TOP_K_VOTE).sum(axis=0)
    return EnsembleResult(per_seed, score, per_seed.std(axis=0), avg_rank, final_rank, votes)


class Predictor:
    def __init__(self, art: Artifacts, device: str = "cpu"):
        self.art = art
        self.device = torch.device(device)
        self.models: list[MarketMoE] = []
        for path in art.weight_files():
            model = build_model(art)
            state = torch.load(path, map_location="cpu", weights_only=True)
            model.load_state_dict(state)
            model.to(self.device).eval()
            self.models.append(model)

    @property
    def n_seeds(self) -> int:
        return len(self.models)

    def _tensors(self, x: np.ndarray, news_emb: np.ndarray, news_mask: np.ndarray):
        def t(a):
            return torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32)).to(self.device)

        return t(x), t(news_emb), t(news_mask)

    def raw_scores(self, x: np.ndarray, news_emb: np.ndarray, news_mask: np.ndarray) -> np.ndarray:
        """One sample: x (1,1,T,N,D) -> (S, N) scores."""
        xt, et, mt = self._tensors(x, news_emb, news_mask)
        out = [seeded_forward(m, xt, et, mt, self.art.noise_seed)[0].cpu().numpy() for m in self.models]
        return np.stack(out)

    def predict(self, x: np.ndarray, news_emb: np.ndarray, news_mask: np.ndarray) -> EnsembleResult:
        return combine(self.raw_scores(x, news_emb, news_mask))
