"""Markov context predictor: n-gram conditioned on count and outs."""

import pickle
from typing import Dict, List

import pandas as pd

from .base import BasePredictorModel, DEFAULT_PITCH_VALUE, MODELS_DIR


class MarkovContextPredictor(BasePredictorModel):
    """N-gram predictor conditioned on balls/strikes/outs.

    Loads a pre-trained prior from training data if available,
    then continues learning online during a game.
    """

    def __init__(self, gram_size: int = 3):
        super().__init__("Markov Context")
        self.gram_size = gram_size
        self.prior_model = self._load_prior()

    def _load_prior(self) -> Dict[str, Dict[str, int]]:
        prior_path = MODELS_DIR / "markov_context.pkl"
        if prior_path.exists():
            with open(prior_path, "rb") as f:
                return pickle.load(f)
        return {}

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        model = {k: dict(v) for k, v in self.prior_model.items()}
        predicted_pitches = []

        for i in range(len(game_stats_df)):
            row = game_stats_df.iloc[i]
            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))

            past = (
                game_stats_df["pitch_type_simplified"]
                .iloc[max(0, i - self.gram_size):i]
                .tolist()
            )

            context_key = self._make_key(past, balls, strikes, outs)
            predicted_pitches.append(self._make_prediction(model, context_key, past))

            actual = game_stats_df["pitch_type_simplified"].iloc[i]
            self._update(model, context_key, actual)

        return predicted_pitches

    def _make_key(self, past: List[str], balls: int, strikes: int, outs: int) -> str:
        if len(past) == self.gram_size:
            return f"{''.join(past)}:{balls}{strikes}{outs}"
        return ""

    def _make_prediction(self, model: dict, key: str, past: List[str]) -> str:
        if key and key in model:
            return max(model[key], key=model[key].get)
        if len(past) == self.gram_size:
            seq_key = "".join(past)
            if seq_key in model:
                return max(model[seq_key], key=model[seq_key].get)
        return DEFAULT_PITCH_VALUE

    def _update(self, model: dict, key: str, pitch: str):
        if not key:
            return
        if key not in model:
            model[key] = {}
        model[key][pitch] = model[key].get(pitch, 0) + 1
