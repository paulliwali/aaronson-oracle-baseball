"""Experiment 1: Temperature tuning and threshold-based prediction for PitchGPT.

Precompute logits per test position once, then apply strategies post-hoc. Much faster
than re-running the model per strategy.
"""

import sys
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn.functional as F

_training_dir = str(Path(__file__).parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import (
    PITCH_CLASSES,
    MODELS_DIR,
    load_all_data,
    make_splits,
    encode_pitch,
    build_pitcher_vocab,
    iter_games,
)
from models.transformer import PitchGPT, PitchGPTConfig


def load_model(device):
    model_path = MODELS_DIR / "pitch_transformer.pt"
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    config = checkpoint["config"]
    pitcher_vocab = checkpoint["pitcher_vocab"]
    model = PitchGPT(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, config, pitcher_vocab


def precompute_logits(model, config, device, pitcher_vocab, test_df):
    """Run model once over test set. Return (all_logits [N,3], all_actuals [N])."""
    all_logits = []
    all_actuals = []

    for game_df in iter_games(test_df):
        n = len(game_df)
        pitch_ids = []
        ctx_data = []
        pitcher_id_raw = int(game_df["pitcher"].iloc[0]) if "pitcher" in game_df.columns else 0
        pitcher_idx = pitcher_vocab.get(pitcher_id_raw, 0)
        pitcher_t = torch.tensor([pitcher_idx], device=device)

        # First pitch: no context. Use argmax-fast sentinel logits.
        first_logit = np.array([10.0, 0.0, 0.0], dtype=np.float32)
        all_logits.append(first_logit)
        all_actuals.append(game_df["pitch_type_simplified"].iloc[0])

        for i in range(n):
            row = game_df.iloc[i]
            pitch_ids.append(encode_pitch(row["pitch_type_simplified"]))
            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))
            inning = min(int(row.get("inning", 1)), 12)
            stand = 0 if str(row.get("stand", "R")) == "L" else 1
            phand = 0 if str(row.get("p_throws", "R")) == "L" else 1
            ctx_data.append([balls, strikes, outs, inning, stand, phand])

            if i == 0:
                continue

            seq_len = min(len(pitch_ids), config.seq_len)
            p_tensor = torch.tensor([pitch_ids[-seq_len:]], device=device)
            c_tensor = torch.tensor([ctx_data[-seq_len:]], device=device)

            with torch.no_grad():
                logits = model(p_tensor, c_tensor, pitcher_t)
                logits_last = logits[0, -1].cpu().numpy()

            all_logits.append(logits_last)
            all_actuals.append(game_df["pitch_type_simplified"].iloc[i])

    return np.array(all_logits), np.array(all_actuals)


def apply_strategy(logits_arr, strategy, **kwargs):
    """Apply prediction strategy to [N,3] logits. Return [N] pred class names."""
    logits_t = torch.from_numpy(logits_arr).float()

    if strategy == "argmax":
        pred_idx = logits_t.argmax(dim=-1).numpy()

    elif strategy == "threshold":
        probs = F.softmax(logits_t, dim=-1).numpy()
        non_fast = probs[:, 1] + probs[:, 2]
        threshold = kwargs.get("threshold", 0.4)
        above = non_fast > threshold
        brk_vs_off = probs[:, 1] > probs[:, 2]
        pred_idx = np.where(above, np.where(brk_vs_off, 1, 2), 0)

    elif strategy == "temperature_threshold":
        temp = kwargs.get("temperature", 1.0)
        probs = F.softmax(logits_t / temp, dim=-1).numpy()
        non_fast = probs[:, 1] + probs[:, 2]
        threshold = kwargs.get("threshold", 0.4)
        above = non_fast > threshold
        brk_vs_off = probs[:, 1] > probs[:, 2]
        pred_idx = np.where(above, np.where(brk_vs_off, 1, 2), 0)

    else:
        pred_idx = logits_t.argmax(dim=-1).numpy()

    return np.array([PITCH_CLASSES[i] for i in pred_idx])


def score(preds, actuals):
    total = len(preds)
    correct = (preds == actuals).sum()
    accuracy = correct / total
    pred_dist = Counter(preds)
    per_class = {}
    for cls in PITCH_CLASSES:
        mask = actuals == cls
        if mask.sum() > 0:
            per_class[cls] = (preds[mask] == cls).sum() / mask.sum()
        else:
            per_class[cls] = 0.0
    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "pred_dist": {k: v / total for k, v in pred_dist.items()},
    }


def run_experiments():
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Device: {device}", flush=True)

    print("Loading model...", flush=True)
    model, config, pitcher_vocab = load_model(device)

    print("Loading data...", flush=True)
    df = load_all_data()
    splits = make_splits(df)
    test_df = splits["test"]
    print(f"Test set: {len(test_df):,} pitches", flush=True)

    print("Precomputing logits (one pass)...", flush=True)
    import time
    t0 = time.time()
    logits_arr, actuals_arr = precompute_logits(model, config, device, pitcher_vocab, test_df)
    print(f"Logits shape: {logits_arr.shape}, took {time.time()-t0:.0f}s", flush=True)

    # Cache logits to disk for reuse
    cache_path = Path(__file__).parent / "test_logits_cache.npz"
    np.savez(cache_path, logits=logits_arr, actuals=actuals_arr)
    print(f"Cached to {cache_path}", flush=True)

    experiments = [("argmax (baseline)", "argmax", {})]
    for threshold in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        experiments.append((f"threshold={threshold:.2f}", "threshold", {"threshold": threshold}))
    for temp in [0.5, 0.7, 1.5, 2.0, 3.0]:
        for threshold in [0.30, 0.35, 0.40, 0.45]:
            experiments.append(
                (f"temp={temp:.1f}+thr={threshold:.2f}", "temperature_threshold",
                 {"temperature": temp, "threshold": threshold})
            )

    print(f"\nRunning {len(experiments)} strategies...\n", flush=True)
    print(f"{'Experiment':<30} {'Accuracy':>8} {'Fast%':>6} {'Brk%':>6} {'Off%':>6} | {'acc_f':>6} {'acc_b':>6} {'acc_o':>6}", flush=True)
    print("-" * 100, flush=True)

    results = []
    for name, strategy, kwargs in experiments:
        preds = apply_strategy(logits_arr, strategy, **kwargs)
        r = score(preds, actuals_arr)
        pf = r["pred_dist"].get("fast", 0) * 100
        pb = r["pred_dist"].get("breaking", 0) * 100
        po = r["pred_dist"].get("off-speed", 0) * 100
        af = r["per_class"].get("fast", 0)
        ab = r["per_class"].get("breaking", 0)
        ao = r["per_class"].get("off-speed", 0)
        print(f"{name:<30} {r['accuracy']:>8.4f} {pf:>5.1f}% {pb:>5.1f}% {po:>5.1f}% | {af:>6.4f} {ab:>6.4f} {ao:>6.4f}", flush=True)
        results.append((name, r))

    actual_dist = Counter(actuals_arr)
    total = len(actuals_arr)
    print(f"\nActual test dist: fast={actual_dist.get('fast',0)/total*100:.1f}%, "
          f"breaking={actual_dist.get('breaking',0)/total*100:.1f}%, "
          f"off-speed={actual_dist.get('off-speed',0)/total*100:.1f}%", flush=True)

    best_name, best_r = max(results, key=lambda x: x[1]["accuracy"])
    print(f"\nBest: {best_name} acc={best_r['accuracy']:.4f}", flush=True)

    return results


if __name__ == "__main__":
    run_experiments()
