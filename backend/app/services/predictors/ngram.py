"""N-gram pattern matching predictor (Aaronson Oracle algorithm)."""

from typing import Dict, List

import pandas as pd

from .base import BasePredictorModel, DEFAULT_PITCH_VALUE, PITCH_GRAM_SIZE


class NGramPredictor(BasePredictorModel):

    def __init__(self, gram_size: int = PITCH_GRAM_SIZE):
        super().__init__(f"N-Gram (n={gram_size})")
        self.gram_size = gram_size

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        predicted_pitches = []
        model: Dict[str, Dict[str, int]] = {}

        for i in range(len(game_stats_df)):
            past_pitches = (
                game_stats_df["pitch_type_simplified"]
                .iloc[max(0, i - self.gram_size):i]
                .to_list()
            )
            next_pitch = game_stats_df["pitch_type_simplified"].iloc[i]
            pitch_gram = self._create_pitch_gram(past_pitches)
            predicted_pitches.append(self._make_prediction(model, pitch_gram))
            self._update_model(model, pitch_gram, next_pitch)

        return predicted_pitches

    def _create_pitch_gram(self, pitches: List[str]) -> str:
        if len(pitches) == self.gram_size:
            return "".join(pitches)
        return ""

    def _update_model(self, model: Dict[str, Dict[str, int]], pitch_gram: str, next_pitch: str):
        if not pitch_gram:
            return
        if pitch_gram in model:
            model[pitch_gram][next_pitch] = model[pitch_gram].get(next_pitch, 0) + 1
        else:
            model[pitch_gram] = {next_pitch: 1}

    def _make_prediction(self, model: Dict[str, Dict[str, int]], pitch_gram: str) -> str:
        if pitch_gram and pitch_gram in model:
            return max(model[pitch_gram], key=model[pitch_gram].get)
        return DEFAULT_PITCH_VALUE
