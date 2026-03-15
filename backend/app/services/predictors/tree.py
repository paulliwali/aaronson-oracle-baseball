"""Random Forest predictor using scikit-learn."""

from typing import List

import numpy as np
import pandas as pd

from .base import BasePredictorModel, DEFAULT_PITCH_VALUE, PITCH_CLASSES, PITCH_TO_IDX, MODELS_DIR

HISTORY_LEN = 5


class TreePredictor(BasePredictorModel):
    """Random Forest with game-state features. Requires trained weights."""

    def __init__(self):
        super().__init__("Random Forest")
        self._model = None
        self._load_attempted = False

    def _load_model(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        model_path = MODELS_DIR / "random_forest.joblib"
        if model_path.exists():
            import joblib
            self._model = joblib.load(model_path)

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        self._load_model()
        if self._model is None:
            return [DEFAULT_PITCH_VALUE] * len(game_stats_df)

        features = self._extract_features(game_stats_df)
        pred_indices = self._model.predict(features)
        return [PITCH_CLASSES[int(i)] for i in pred_indices]

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        features = []
        pitch_counts = np.zeros(len(PITCH_CLASSES), dtype=np.float32)

        for i in range(len(df)):
            row = df.iloc[i]
            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))
            inning = int(row.get("inning", 1))

            home_score = int(row.get("home_score", 0))
            away_score = int(row.get("away_score", 0))
            inning_topbot = row.get("inning_topbot", "Top")
            score_diff = (home_score - away_score) if inning_topbot == "Top" else (away_score - home_score)

            history = []
            for j in range(HISTORY_LEN):
                idx = i - HISTORY_LEN + j
                if idx >= 0:
                    prev_pitch = df.iloc[idx]["pitch_type_simplified"]
                    one_hot = [0.0] * len(PITCH_CLASSES)
                    one_hot[PITCH_TO_IDX.get(prev_pitch, 0)] = 1.0
                    history.extend(one_hot)
                else:
                    history.extend([0.0] * len(PITCH_CLASSES))

            dist = pitch_counts / pitch_counts.sum() if i > 0 else np.ones(len(PITCH_CLASSES)) / len(PITCH_CLASSES)

            feat = [
                balls / 3.0, strikes / 2.0, outs / 2.0,
                min(inning, 12) / 12.0, score_diff / 10.0,
            ] + history + dist.tolist()
            features.append(feat)

            pitch_type = row["pitch_type_simplified"]
            pitch_counts[PITCH_TO_IDX.get(pitch_type, 0)] += 1

        return np.array(features, dtype=np.float32)
