"""Base class and shared constants for prediction models."""

from pathlib import Path
from typing import List

import pandas as pd


DEFAULT_PITCH_VALUE = "fast"
PITCH_GRAM_SIZE = 3
PITCH_CLASSES = ["fast", "breaking", "off-speed"]
PITCH_TO_IDX = {p: i for i, p in enumerate(PITCH_CLASSES)}
MODELS_DIR = Path(__file__).parent.parent.parent.parent.parent / "model_artifacts"


class BasePredictorModel:
    """Base class for prediction models"""

    def __init__(self, name: str):
        self.name = name

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        """Make predictions for all pitches in a game"""
        raise NotImplementedError

    def calculate_accuracy(self, predictions: List[str], actuals: pd.Series) -> float:
        correct = sum(p == a for p, a in zip(predictions, actuals))
        return round(correct / len(predictions), 4) if predictions else 0.0

    def calculate_rolling_accuracy(self, predictions: List[str], actuals: pd.Series) -> List[float]:
        correct_count = 0
        rolling_accuracy = []
        for i, (pred, actual) in enumerate(zip(predictions, actuals), start=1):
            if pred == actual:
                correct_count += 1
            rolling_accuracy.append(correct_count / i)
        return rolling_accuracy
