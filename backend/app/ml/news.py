"""News features: PhoBERT title embeddings and the per-ticker news pick.

Notebook ``midmoe-vn-data-prepare`` Phase 8-9:
* model ``vinai/phobert-base``, raw titles (no word segmentation), max_length 64,
  embedding = ``last_hidden_state.mean(dim=1)`` (padding tokens included).
* for each ticker and window end date, take the single most recent article
  dated within [end - 5 calendar days, end]; none -> zero vector, mask 0.

The notebook padded each batch of 32 to its longest title, so a title's vector
depended slightly on its neighbours. Here every title is padded to 64 tokens,
which is deterministic and close to the training distribution.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Iterable

import numpy as np

log = logging.getLogger(__name__)

EMB_DIM = 768
LOOKBACK_DAYS = 5
MODEL_NAME = "vinai/phobert-base"


class PhoBERTEmbedder:
    def __init__(self, model_name: str = MODEL_NAME, max_length: int = 64, batch_size: int = 32):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self._tok = None
        self._model = None

    def _load(self):
        if self._model is None:
            import torch  # noqa: F401
            from transformers import AutoModel, AutoTokenizer

            log.info("Loading %s (lần đầu sẽ tải ~540 MB từ Hugging Face)", self.model_name)
            self._tok = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name).eval()

    def encode(self, titles: list[str]) -> np.ndarray:
        if not titles:
            return np.zeros((0, EMB_DIM), dtype=np.float32)
        self._load()
        import torch

        out = []
        for i in range(0, len(titles), self.batch_size):
            batch = titles[i : i + self.batch_size]
            enc = self._tok(batch, padding="max_length", truncation=True, max_length=self.max_length, return_tensors="pt")
            with torch.no_grad():
                hidden = self._model(**enc).last_hidden_state
            out.append(hidden.mean(dim=1).cpu().numpy().astype(np.float32))
        return np.concatenate(out, axis=0)


def pick_news(items: Iterable[tuple[date, int]], as_of: date, lookback_days: int = LOOKBACK_DAYS) -> int | None:
    """items: (article_date, id) for one ticker. Returns the id of the newest article
    dated in [as_of - lookback_days, as_of], or None."""
    lower = as_of - timedelta(days=lookback_days)
    best: tuple[date, int] | None = None
    for d, i in items:
        if lower <= d <= as_of and (best is None or d > best[0] or (d == best[0] and i > best[1])):
            best = (d, i)
    return best[1] if best else None
