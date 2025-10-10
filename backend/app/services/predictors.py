"""Prediction models for pitch type prediction"""

from typing import List, Dict
import pandas as pd


DEFAULT_PITCH_VALUE = "fast"
PITCH_GRAM_SIZE = 3


class BasePredictorModel:
    """Base class for prediction models"""

    def __init__(self, name: str):
        self.name = name

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        """Make predictions for all pitches in a game"""
        raise NotImplementedError

    def calculate_accuracy(self, predictions: List[str], actuals: pd.Series) -> float:
        """Calculate overall accuracy"""
        correct = sum(p == a for p, a in zip(predictions, actuals))
        return round(correct / len(predictions), 4) if predictions else 0.0

    def calculate_rolling_accuracy(self, predictions: List[str], actuals: pd.Series) -> List[float]:
        """Calculate rolling accuracy over the series"""
        correct_count = 0
        rolling_accuracy = []

        for i, (pred, actual) in enumerate(zip(predictions, actuals), start=1):
            if pred == actual:
                correct_count += 1
            rolling_accuracy.append(correct_count / i)

        return rolling_accuracy


class NaivePredictor(BasePredictorModel):
    """Naive baseline that always predicts the most common pitch type"""

    def __init__(self):
        super().__init__("Naive (Always Fast)")

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        """Always predict 'fast'"""
        return [DEFAULT_PITCH_VALUE] * len(game_stats_df)


class NGramPredictor(BasePredictorModel):
    """N-gram pattern matching predictor (Aaronson Oracle algorithm)"""

    def __init__(self, gram_size: int = PITCH_GRAM_SIZE):
        super().__init__(f"N-Gram (n={gram_size})")
        self.gram_size = gram_size

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        """Predict using n-gram pattern matching"""
        predicted_pitches = []
        model: Dict[str, Dict[str, int]] = {}

        for i in range(len(game_stats_df)):
            past_pitches = (
                game_stats_df["pitch_type_simplified"]
                .iloc[max(0, i - self.gram_size) : i]
                .to_list()
            )

            next_pitch = game_stats_df["pitch_type_simplified"].iloc[i]
            pitch_gram = self._create_pitch_gram(past_pitches)

            # Make prediction
            predicted_pitches.append(self._make_prediction(model, pitch_gram))

            # Update model
            self._update_model(model, pitch_gram, next_pitch)

        return predicted_pitches

    def _create_pitch_gram(self, pitches: List[str]) -> str:
        """Create a pitch gram string from list of pitches"""
        if len(pitches) == self.gram_size:
            return "".join(pitches)
        return ""

    def _update_model(self, model: Dict[str, Dict[str, int]], pitch_gram: str, next_pitch: str):
        """Update the model with observed pitch sequence"""
        if not pitch_gram:
            return

        if pitch_gram in model:
            model[pitch_gram][next_pitch] = model[pitch_gram].get(next_pitch, 0) + 1
        else:
            model[pitch_gram] = {next_pitch: 1}

    def _make_prediction(self, model: Dict[str, Dict[str, int]], pitch_gram: str) -> str:
        """Make a prediction based on the current pitch gram"""
        if pitch_gram and pitch_gram in model:
            return max(model[pitch_gram], key=model[pitch_gram].get)
        return DEFAULT_PITCH_VALUE


class FrequencyPredictor(BasePredictorModel):
    """Predicts by sampling from the game's pitch type distribution"""

    def __init__(self):
        super().__init__("Frequency-Based (Oracle)")

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        """Predict by sampling from the known distribution of the entire game.

        This is an "oracle" model that has perfect knowledge of the game's pitch
        distribution. In future iterations, this distribution could be estimated
        from the pitcher's historical games instead.
        """
        import random

        # Get the full game distribution (oracle knowledge)
        pitch_counts = game_stats_df["pitch_type_simplified"].value_counts().to_dict()

        # Convert counts to probabilities
        total_pitches = sum(pitch_counts.values())
        pitch_types = list(pitch_counts.keys())
        probabilities = [pitch_counts[pt] / total_pitches for pt in pitch_types]

        # Sample from the distribution for each prediction
        predicted_pitches = []
        for _ in range(len(game_stats_df)):
            prediction = random.choices(pitch_types, weights=probabilities, k=1)[0]
            predicted_pitches.append(prediction)

        return predicted_pitches


# Registry of available models
AVAILABLE_MODELS = [
    NaivePredictor(),
    NGramPredictor(gram_size=3),
    NGramPredictor(gram_size=4),
    FrequencyPredictor(),
]
