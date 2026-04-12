"""
Shared data preparation and evaluation harness for pitch prediction models.
Loads training data, creates splits, provides dataloaders and evaluation.

Usage: uv run python training/prepare.py  (to verify data is ready)
"""

from pathlib import Path
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

PITCH_CLASSES = ["fast", "breaking", "off-speed"]
PITCH_TO_IDX = {p: i for i, p in enumerate(PITCH_CLASSES)}
NUM_CLASSES = len(PITCH_CLASSES)
SEED = 42

DATA_DIR = Path(__file__).parent.parent / "data" / "training"
MODELS_DIR = Path(__file__).parent.parent / "model_artifacts"

# Feature engineering constants
HISTORY_LEN = 5
NUM_FEATURES = 5 + HISTORY_LEN * NUM_CLASSES + NUM_CLASSES  # 23 features


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_data() -> pd.DataFrame:
    """Load all pitcher-season CSVs into a single DataFrame."""
    frames = []
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path)
        stem = csv_path.stem
        parts = stem.rsplit("_", 1)
        df["source_file"] = csv_path.name
        if len(parts) == 2:
            df["season"] = int(parts[1])
        frames.append(df)

    if not frames:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

    combined = pd.concat(frames, ignore_index=True)
    combined["game_date"] = pd.to_datetime(combined["game_date"])
    return combined


# ---------------------------------------------------------------------------
# Splits
# ---------------------------------------------------------------------------

def make_splits(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Per-pitcher chronological split (70/15/15).

    Each pitcher's games are sorted by date. The first 70% become train,
    next 15% val, last 15% test. This tests temporal generalization while
    ensuring every pitcher appears in all splits.
    """
    train_parts, val_parts, test_parts = [], [], []
    pitcher_col = "pitcher" if "pitcher" in df.columns else "player_name"

    for _, pitcher_df in df.groupby(pitcher_col):
        dates = sorted(pitcher_df["game_date"].unique())
        n = len(dates)
        train_end = int(n * 0.70)
        val_end = int(n * 0.85)

        train_dates = set(dates[:train_end])
        val_dates = set(dates[train_end:val_end])
        test_dates = set(dates[val_end:])

        train_parts.append(pitcher_df[pitcher_df["game_date"].isin(train_dates)])
        val_parts.append(pitcher_df[pitcher_df["game_date"].isin(val_dates)])
        test_parts.append(pitcher_df[pitcher_df["game_date"].isin(test_dates)])

    return {
        "train": pd.concat(train_parts, ignore_index=True),
        "val": pd.concat(val_parts, ignore_index=True),
        "test": pd.concat(test_parts, ignore_index=True),
    }


# ---------------------------------------------------------------------------
# Game iteration
# ---------------------------------------------------------------------------

def iter_games(df: pd.DataFrame):
    """Yield individual game DataFrames, sorted by pitch_number."""
    pitcher_col = "pitcher" if "pitcher" in df.columns else "player_name"
    for (pitcher, date), game_df in df.groupby([pitcher_col, "game_date"]):
        yield game_df.sort_values("pitch_number").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def encode_pitch(pitch: str) -> int:
    return PITCH_TO_IDX.get(pitch, 0)


def decode_pitch(idx: int) -> str:
    return PITCH_CLASSES[idx]


def extract_game_features(game_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Extract features and labels for a single game.

    Features per pitch (23 total):
    - balls/3, strikes/2, outs/2, inning/12, score_diff/10   (5)
    - previous 5 pitch types one-hot                          (15)
    - running pitch type distribution                         (3)

    Returns (features, labels) as numpy arrays.
    """
    n = len(game_df)
    features = np.zeros((n, NUM_FEATURES), dtype=np.float32)
    labels = np.zeros(n, dtype=np.int64)
    pitch_counts = np.zeros(NUM_CLASSES, dtype=np.float32)

    for i in range(n):
        row = game_df.iloc[i]

        balls = int(row.get("balls", 0))
        strikes = int(row.get("strikes", 0))
        outs = int(row.get("outs_when_up", 0))
        inning = int(row.get("inning", 1))

        home_score = int(row.get("home_score", 0))
        away_score = int(row.get("away_score", 0))
        inning_topbot = row.get("inning_topbot", "Top")
        score_diff = (home_score - away_score) if inning_topbot == "Top" else (away_score - home_score)

        features[i, 0] = balls / 3.0
        features[i, 1] = strikes / 2.0
        features[i, 2] = outs / 2.0
        features[i, 3] = min(inning, 12) / 12.0
        features[i, 4] = score_diff / 10.0

        # Previous pitch history (one-hot)
        for j in range(HISTORY_LEN):
            idx = i - HISTORY_LEN + j
            if idx >= 0:
                prev_pitch = game_df.iloc[idx]["pitch_type_simplified"]
                features[i, 5 + j * NUM_CLASSES + encode_pitch(prev_pitch)] = 1.0

        # Running distribution
        if i > 0:
            features[i, 5 + HISTORY_LEN * NUM_CLASSES:] = pitch_counts / pitch_counts.sum()
        else:
            features[i, 5 + HISTORY_LEN * NUM_CLASSES:] = 1.0 / NUM_CLASSES

        label = encode_pitch(row["pitch_type_simplified"])
        labels[i] = label
        pitch_counts[label] += 1

    return features, labels


def extract_all_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Extract features from all games in a DataFrame."""
    all_features = []
    all_labels = []
    for game_df in iter_games(df):
        feat, lab = extract_game_features(game_df)
        all_features.append(feat)
        all_labels.append(lab)
    if not all_features:
        return np.array([]).reshape(0, NUM_FEATURES), np.array([], dtype=np.int64)
    return np.concatenate(all_features), np.concatenate(all_labels)


def _handed_to_idx(series: pd.Series) -> np.ndarray:
    """Map L/R handedness to 0/1. Missing values default to R (1)."""
    return series.fillna("R").map({"L": 0, "R": 1}).fillna(1).values.astype(np.int64)


def build_pitcher_vocab(df: pd.DataFrame) -> dict:
    """Build pitcher_id -> idx mapping. Reserves idx 0 for unknown pitchers."""
    pitcher_col = "pitcher" if "pitcher" in df.columns else "player_name"
    unique = sorted(df[pitcher_col].dropna().unique().tolist())
    return {int(pid): i + 1 for i, pid in enumerate(unique)}


def extract_sequences(df: pd.DataFrame, seq_len: int = 256, pitcher_vocab: dict = None):
    """Extract pitch sequences for sequence model training.

    Returns lists of (context_array, pitch_array, pitcher_idx) per game.
    context_array: (T, 6) int64 — [balls, strikes, outs, inning, stand, p_throws]
    pitch_array: (T,) int64 — pitch type indices, padded with -1
    pitcher_idx: int — vocab index of the pitcher (0 = unknown)
    """
    sequences_ctx = []
    sequences_pitch = []
    sequences_pitcher = []

    pitcher_col = "pitcher" if "pitcher" in df.columns else "player_name"

    for game_df in iter_games(df):
        pitches = game_df["pitch_type_simplified"].map(encode_pitch).values.astype(np.int64)
        balls = game_df["balls"].fillna(0).values.astype(np.int64)
        strikes = game_df["strikes"].fillna(0).values.astype(np.int64)
        outs = game_df["outs_when_up"].fillna(0).values.astype(np.int64)
        innings = game_df["inning"].fillna(1).values.astype(np.int64).clip(1, 12)
        stand = _handed_to_idx(game_df["stand"]) if "stand" in game_df.columns else np.ones(len(pitches), dtype=np.int64)
        phand = _handed_to_idx(game_df["p_throws"]) if "p_throws" in game_df.columns else np.ones(len(pitches), dtype=np.int64)

        ctx = np.stack([balls, strikes, outs, innings, stand, phand], axis=1)

        pitcher_id = int(game_df[pitcher_col].iloc[0]) if pitcher_col in game_df.columns else 0
        pitcher_idx = pitcher_vocab.get(pitcher_id, 0) if pitcher_vocab else 0

        n = len(pitches)
        if n > seq_len:
            pitches = pitches[:seq_len]
            ctx = ctx[:seq_len]
        elif n < seq_len:
            pad_len = seq_len - n
            pitches = np.pad(pitches, (0, pad_len), constant_values=-1)
            ctx = np.pad(ctx, ((0, pad_len), (0, 0)), constant_values=0)

        sequences_pitch.append(pitches)
        sequences_ctx.append(ctx)
        sequences_pitcher.append(pitcher_idx)

    return sequences_ctx, sequences_pitch, sequences_pitcher


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(predict_fn: Callable[[pd.DataFrame], List[str]], split: str = "test") -> dict:
    """Evaluate a prediction function on the specified split.

    predict_fn: takes a game DataFrame, returns List[str] of predictions
                (one per pitch, same length as input DataFrame)

    Returns dict with:
        accuracy: float — overall accuracy (THE metric to optimize)
        per_class: dict — per-class accuracy
        n_pitches: int — total pitches evaluated
        n_games: int — total games evaluated
    """
    df = load_all_data()
    splits = make_splits(df)
    eval_df = splits[split]

    all_preds = []
    all_actuals = []
    n_games = 0

    for game_df in iter_games(eval_df):
        preds = predict_fn(game_df)
        actuals = game_df["pitch_type_simplified"].tolist()
        assert len(preds) == len(actuals), (
            f"predict_fn returned {len(preds)} predictions for {len(actuals)} pitches"
        )
        all_preds.extend(preds)
        all_actuals.extend(actuals)
        n_games += 1

    if not all_preds:
        return {"accuracy": 0.0, "per_class": {}, "n_pitches": 0, "n_games": 0}

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

    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "n_pitches": len(all_preds),
        "n_games": n_games,
    }


# ---------------------------------------------------------------------------
# Main — verify data is ready
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Verifying data...")
    df = load_all_data()
    print(f"Total: {len(df):,} pitches from {df['source_file'].nunique()} files")
    print()

    splits = make_splits(df)
    for name, part in splits.items():
        n_games = sum(1 for _ in iter_games(part))
        print(f"  {name:5s}: {len(part):>7,} pitches, {n_games:>4} games")

    print()
    dist = df["pitch_type_simplified"].value_counts()
    print("Pitch distribution:")
    for cls, count in dist.items():
        print(f"  {cls:12s}: {count:>7,} ({count/len(df)*100:.1f}%)")

    print()
    print(f"Feature vector size: {NUM_FEATURES}")
    print()
    print("Data is ready. Run: uv run python training/train.py <model>")
