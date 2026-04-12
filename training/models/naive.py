"""Naive baseline: always predicts 'fast'.

No training required. Serves as the baseline to beat.
"""

import sys
from pathlib import Path

_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import PITCH_CLASSES, evaluate


def make_predict_fn():
    def predict_fn(game_df):
        return ["fast"] * len(game_df)
    return predict_fn


def train():
    """No training needed -- just evaluate the baseline."""
    print("Naive model: always predicts 'fast'")
    print("No training required.\n")

    predict_fn = make_predict_fn()
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
