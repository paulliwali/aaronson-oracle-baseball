"""Markov context predictor: n-gram conditioned on count and outs.

Combines pitch sequence patterns with game state (balls, strikes, outs)
for context-aware predictions. Learns online during each game.
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
            row = game_df.iloc[i]
            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))

            past = game_df["pitch_type_simplified"].iloc[max(0, i - gram_size):i].tolist()
            actual = game_df["pitch_type_simplified"].iloc[i]

            # Build context key: pitch sequence + count/outs
            if len(past) == gram_size:
                ctx_key = f"{''.join(past)}:{balls}{strikes}{outs}"
                seq_key = "".join(past)
            else:
                ctx_key = ""
                seq_key = ""

            # Predict: try context key first, fall back to sequence only
            if ctx_key and ctx_key in model:
                pred = max(model[ctx_key], key=model[ctx_key].get)
            elif seq_key and seq_key in model:
                pred = max(model[seq_key], key=model[seq_key].get)
            else:
                pred = DEFAULT_PITCH
            predictions.append(pred)

            # Update
            if ctx_key:
                if ctx_key not in model:
                    model[ctx_key] = {}
                model[ctx_key][actual] = model[ctx_key].get(actual, 0) + 1

        return predictions

    return predict_fn


def train(gram_size=3):
    """No training needed -- evaluate the Markov context model."""
    print(f"Markov Context model (n={gram_size}): online learning with count/outs context")

    predict_fn = make_predict_fn(gram_size)
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
