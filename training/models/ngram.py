"""N-gram pattern matching predictor (Aaronson Oracle algorithm).

Builds an n-gram model online during each game, predicting the next pitch
based on the most recent n-pitch pattern.
"""

import sys
from pathlib import Path

_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import evaluate

DEFAULT_PITCH = "fast"


def make_predict_fn(gram_size=3):
    def predict_fn(game_df):
        model = {}
        predictions = []

        for i in range(len(game_df)):
            past = game_df["pitch_type_simplified"].iloc[max(0, i - gram_size):i].tolist()
            actual = game_df["pitch_type_simplified"].iloc[i]

            gram = "".join(past) if len(past) == gram_size else ""

            # Predict
            if gram and gram in model:
                pred = max(model[gram], key=model[gram].get)
            else:
                pred = DEFAULT_PITCH
            predictions.append(pred)

            # Update
            if gram:
                if gram not in model:
                    model[gram] = {}
                model[gram][actual] = model[gram].get(actual, 0) + 1

        return predictions

    return predict_fn


def train(gram_size=3):
    """No training needed -- evaluate the n-gram model."""
    print(f"N-Gram model (n={gram_size}): online learning, no pre-training")

    predict_fn = make_predict_fn(gram_size)
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
