"""Benchmark prediction models against the test split.

Produces:
- Overall model comparison (per-class + confusion)
- Per-pitcher breakdown with lift over naive baseline (exposes junk-baller performance)
"""

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
NAIVE_NAME = "Naive (Always Fast)"


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


def evaluate_per_pitcher(models: list, df: pd.DataFrame) -> dict:
    """Return nested dict: {pitcher_name: {model_name: {accuracy, n_pitches, fast_pct}}}."""
    pitcher_col = "pitcher" if "pitcher" in df.columns else "player_name"
    results = {}

    for pitcher_id, pitcher_df in df.groupby(pitcher_col):
        name = str(pitcher_df["player_name"].iloc[0]) if "player_name" in pitcher_df.columns else str(pitcher_id)
        fast_pct = (pitcher_df["pitch_type_simplified"] == "fast").mean()
        n_pitches = len(pitcher_df)

        pitcher_results = {"fast_pct": round(float(fast_pct), 4), "n_pitches": n_pitches, "models": {}}
        for model in models:
            all_preds = []
            all_actuals = []
            for game_df in iter_games(pitcher_df):
                preds = model.predict(game_df)
                all_preds.extend(preds)
                all_actuals.extend(game_df["pitch_type_simplified"].tolist())
            if all_preds:
                acc = sum(p == a for p, a in zip(all_preds, all_actuals)) / len(all_preds)
            else:
                acc = 0.0
            pitcher_results["models"][model.name] = round(acc, 4)

        results[name] = pitcher_results

    return results


def generate_model_card(results: dict, per_pitcher: dict):
    lines = [
        "# Model Card: Pitch Prediction Models",
        "",
        "## Overall Benchmark",
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
    lines.append("## Per-Pitcher Lift Over Naive Baseline")
    lines.append("")
    lines.append("Sorted by fastball rate (low = junk ballers, high = fastball-heavy).")
    lines.append("**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.")
    lines.append("")

    model_names = [m for m in results.keys() if m != NAIVE_NAME]
    header = "| Pitcher | Fast% | N | Naive | " + " | ".join(model_names) + " | Best Lift |"
    sep = "|---------|-------|---|-------|" + "|".join(["-" * max(len(m), 6) for m in model_names]) + "|----------|"
    lines.append(header)
    lines.append(sep)

    sorted_pitchers = sorted(per_pitcher.items(), key=lambda kv: kv[1]["fast_pct"])
    for name, data in sorted_pitchers:
        naive_acc = data["models"].get(NAIVE_NAME, 0.0)
        row = [
            name,
            f"{data['fast_pct']*100:.1f}%",
            f"{data['n_pitches']:,}",
            f"{naive_acc:.3f}",
        ]
        best_other = 0.0
        for m in model_names:
            acc = data["models"].get(m, 0.0)
            row.append(f"{acc:.3f}")
            if acc > best_other:
                best_other = acc
        lift = best_other - naive_acc
        sign = "+" if lift >= 0 else ""
        row.append(f"{sign}{lift:.3f}")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Confusion Matrices")
    lines.append("")
    for model_name, metrics in results.items():
        if "confusion" in metrics:
            lines.append(f"<details><summary>{model_name}</summary>")
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

    print("Per-pitcher breakdown...")
    per_pitcher = evaluate_per_pitcher(AVAILABLE_MODELS, test_df)
    for name, data in sorted(per_pitcher.items(), key=lambda kv: kv[1]["fast_pct"]):
        naive = data["models"].get(NAIVE_NAME, 0.0)
        best = max((v for k, v in data["models"].items() if k != NAIVE_NAME), default=0.0)
        lift = best - naive
        print(f"  {name:30s} fast={data['fast_pct']*100:5.1f}%  naive={naive:.3f}  best={best:.3f}  lift={lift:+.3f}")

    results_path = PROJECT_ROOT / "training" / "benchmark_results.json"
    with open(results_path, "w") as f:
        json.dump({"overall": results, "per_pitcher": per_pitcher}, f, indent=2)
    print(f"\nSaved results to {results_path}")

    generate_model_card(results, per_pitcher)


if __name__ == "__main__":
    main()
