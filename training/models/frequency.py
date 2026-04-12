"""Frequency-based oracle predictor.

Samples from the game's full pitch type distribution (uses oracle
knowledge of the entire game's pitch mix).
"""

import random
import sys
from pathlib import Path

_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import evaluate


def make_predict_fn():
    def predict_fn(game_df):
        pitch_counts = game_df["pitch_type_simplified"].value_counts().to_dict()
        total = sum(pitch_counts.values())
        types = list(pitch_counts.keys())
        probs = [pitch_counts[t] / total for t in types]

        return [
            random.choices(types, weights=probs, k=1)[0]
            for _ in range(len(game_df))
        ]

    return predict_fn


def train():
    """No training needed -- evaluate the frequency oracle."""
    print("Frequency-Based Oracle: samples from game's pitch distribution")
    print("No training required (uses oracle knowledge).\n")

    predict_fn = make_predict_fn()
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
