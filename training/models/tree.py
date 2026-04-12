"""Random Forest pitch predictor.

Uses per-pitch features (count, inning, pitch history, running distribution)
to predict pitch type.
"""

import time

import joblib

import sys
from pathlib import Path

_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import (
    PITCH_CLASSES,
    MODELS_DIR,
    load_all_data,
    make_splits,
    extract_all_features,
    evaluate,
    iter_games,
    decode_pitch,
)


def make_predict_fn(clf):
    """Create a predict_fn compatible with prepare.evaluate()."""
    from prepare import extract_game_features

    def predict_fn(game_df):
        features, _ = extract_game_features(game_df)
        pred_indices = clf.predict(features)
        return [decode_pitch(int(idx)) for idx in pred_indices]

    return predict_fn


def train(n_estimators: int = 200, max_depth: int = 20):
    """Train a Random Forest classifier on pitch features."""
    t_start = time.time()

    print("Loading data...")
    df = load_all_data()
    splits = make_splits(df)
    print(f"Train: {len(splits['train']):,} | Val: {len(splits['val']):,} | Test: {len(splits['test']):,}")

    print("Extracting features...")
    train_features, train_labels = extract_all_features(splits["train"])
    print(f"Train features: {train_features.shape}")

    from sklearn.ensemble import RandomForestClassifier

    print(f"\nTraining Random Forest (n_estimators={n_estimators}, max_depth={max_depth})...")
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        n_jobs=-1,
        random_state=42,
    )
    clf.fit(train_features, train_labels)

    train_time = time.time() - t_start
    print(f"Training took {train_time:.0f}s")

    # Save
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "random_forest.joblib"
    joblib.dump(clf, model_path)
    print(f"Saved to {model_path}")

    # Evaluate
    print("Evaluating on test set...")
    predict_fn = make_predict_fn(clf)
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"training_seconds: {train_time:.1f}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
