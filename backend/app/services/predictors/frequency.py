"""Frequency-based oracle predictor."""

import random
from typing import List

import pandas as pd

from .base import BasePredictorModel


class FrequencyPredictor(BasePredictorModel):
    """Samples from the game's full pitch type distribution (oracle knowledge)."""

    def __init__(self):
        super().__init__("Frequency-Based (Oracle)")

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        pitch_counts = game_stats_df["pitch_type_simplified"].value_counts().to_dict()
        total_pitches = sum(pitch_counts.values())
        pitch_types = list(pitch_counts.keys())
        probabilities = [pitch_counts[pt] / total_pitches for pt in pitch_types]

        return [
            random.choices(pitch_types, weights=probabilities, k=1)[0]
            for _ in range(len(game_stats_df))
        ]
