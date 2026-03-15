"""Prediction models registry.

Each model lives in its own file:
    base.py        — BasePredictorModel + shared constants
    naive.py       — NaivePredictor (always fast)
    ngram.py       — NGramPredictor (Aaronson Oracle)
    frequency.py   — FrequencyPredictor (oracle distribution)
    markov.py      — MarkovContextPredictor (n-gram + count/outs)
    tree.py        — TreePredictor (Random Forest, requires weights)
    transformer.py — TransformerPredictor (PitchGPT, requires weights)
"""

from typing import List

from .base import BasePredictorModel, MODELS_DIR
from .naive import NaivePredictor
from .ngram import NGramPredictor
from .frequency import FrequencyPredictor
from .markov import MarkovContextPredictor
from .tree import TreePredictor
from .transformer import TransformerPredictor


def _build_model_registry() -> List[BasePredictorModel]:
    """Build the list of available models, including those with trained weights."""
    models: List[BasePredictorModel] = [
        NaivePredictor(),
        NGramPredictor(gram_size=3),
        NGramPredictor(gram_size=4),
        FrequencyPredictor(),
        MarkovContextPredictor(),
    ]

    if (MODELS_DIR / "random_forest.joblib").exists():
        models.append(TreePredictor())

    if (MODELS_DIR / "pitch_transformer.pt").exists():
        models.append(TransformerPredictor())

    return models


AVAILABLE_MODELS = _build_model_registry()
