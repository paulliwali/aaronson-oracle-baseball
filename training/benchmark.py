"""Benchmark prediction models against the test split."""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "training"))

from app.services.predictors import AVAILABLE_MODELS, BasePredictorModel
from prepare import load_all_data, make_splits, iter_games, PITCH_CLASSES


MODEL_CARD_PATH = PROJECT_ROOT / "MODEL_CARD.md"


def evaluate_model_on_games(model: BasePredictorModel, df: pd.DataFrame) -> dict:
    """Run a model on all games in df and compute metrics."""
    all_preds = []
    all_actuals = []

    for game_df in iter_games(df):
        preds = model.predict(game_df)
        actuals = game_df["pitch_type_simplified"].tolist()
        all_preds.extend(preds)
        all_actuals.extend(actuals)

    if not all_preds:
        return {"accuracy": 0.0, "per_class": {}, "n_pitches": 0}

    correct = sum(p == a for p, a in zip(all_preds, all_actuals))
    accuracy = correct / len(all_preds)

    per_class = {}
    for cls in PITCH_CLASSES:
        cls_indices = [i for i, a in enumerate(all_actuals) if a == cls]
        if cls_indices:
            cls_correct = sum(all_preds[i] == all_actuals[i] for i in cls_indices)
            per_class[cls] = cls_correct / len(cls_indices)
        else:
            per_class[cls] = 0.0

    confusion = {actual: {pred: 0 for pred in PITCH_CLASSES} for actual in PITCH_CLASSES}
    for p, a in zip(all_preds, all_actuals):
        if a in confusion and p in confusion[a]:
            confusion[a][p] += 1

    return {
        "accuracy": round(accuracy, 4),
        "per_class": {k: round(v, 4) for k, v in per_class.items()},
        "confusion": confusion,
        "n_pitches": len(all_preds),
    }


def generate_model_card(results: dict):
    lines = [
        "# Model Card: Pitch Prediction Models",
        "",
        "## Benchmark Results",
        "",
        "All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.",
        "",
        "| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |",
        "|-------|---------|------|----------|-----------|-----------|",
    ]

    for model_name, metrics in results.items():
        pc = metrics["per_class"]
        lines.append(
            f"| {model_name} "
            f"| {metrics['accuracy']:.4f} "
            f"| {pc.get('fast', 0):.4f} "
            f"| {pc.get('breaking', 0):.4f} "
            f"| {pc.get('off-speed', 0):.4f} "
            f"| {metrics['n_pitches']:,} |"
        )

    lines.append("")

    for model_name, metrics in results.items():
        if "confusion" in metrics:
            lines.append(f"<details><summary>Confusion: {model_name}</summary>")
            lines.append("")
            lines.append("| Actual \\ Predicted | fast | breaking | off-speed |")
            lines.append("|-------------------|------|----------|-----------|")
            for actual in PITCH_CLASSES:
                row = metrics["confusion"][actual]
                lines.append(
                    f"| {actual} | {row['fast']} | {row['breaking']} | {row['off-speed']} |"
                )
            lines.append("")
            lines.append("</details>")
            lines.append("")

    with open(MODEL_CARD_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"\nWrote {MODEL_CARD_PATH}")


def main():
    print("Loading data...")
    df = load_all_data()
    splits = make_splits(df)
    test_df = splits["test"]

    n_games = sum(1 for _ in iter_games(test_df))
    print(f"Test set: {len(test_df):,} pitches, {n_games} games")

    dist = test_df["pitch_type_simplified"].value_counts()
    print(f"Distribution: {dict(dist)}")
    print()

    results = {}
    for model in AVAILABLE_MODELS:
        metrics = evaluate_model_on_games(model, test_df)
        results[model.name] = metrics
        print(f"  {model.name:30s} -> {metrics['accuracy']:.4f}")
        for cls, acc in metrics["per_class"].items():
            print(f"    {cls:12s}: {acc:.4f}")
        print()

    results_path = PROJECT_ROOT / "training" / "benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved results to {results_path}")

    generate_model_card(results)


if __name__ == "__main__":
    main()
