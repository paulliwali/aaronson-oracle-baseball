"""Naive baseline: always predicts 'fast'."""

from typing import List

import pandas as pd

from .base import BasePredictorModel, DEFAULT_PITCH_VALUE


class NaivePredictor(BasePredictorModel):

    def __init__(self):
        super().__init__("Naive (Always Fast)")

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        return [DEFAULT_PITCH_VALUE] * len(game_stats_df)
