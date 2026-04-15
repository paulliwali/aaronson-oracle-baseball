"""Experiment 2 & 3: Focal loss and class-weighted loss for PitchGPT.

Retrains PitchGPT with modified loss functions to address the
"always predict fastball" problem.
"""

import sys
import time
from pathlib import Path
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

_training_dir = str(Path(__file__).parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import (
    PITCH_CLASSES,
    NUM_CLASSES,
    MODELS_DIR,
    load_all_data,
    make_splits,
    extract_sequences,
    encode_pitch,
    build_pitcher_vocab,
    iter_games,
)
from models.transformer import PitchGPT, PitchGPTConfig


class FocalLoss(nn.Module):
    """Focal loss: down-weights easy examples, up-weights hard ones."""
    def __init__(self, gamma=2.0, alpha=None):
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha  # per-class weights tensor

    def forward(self, logits, targets):
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        pt = torch.exp(-ce_loss)  # probability of correct class
        focal_weight = (1 - pt) ** self.gamma

        if self.alpha is not None:
            alpha_t = self.alpha[targets]
            focal_weight = alpha_t * focal_weight

        return (focal_weight * ce_loss).mean()


def compute_class_weights(train_df, mode="inverse"):
    """Compute class weights from training data."""
    counts = train_df["pitch_type_simplified"].value_counts()
    total = len(train_df)
    n_classes = NUM_CLASSES

    weights = torch.zeros(n_classes)
    for idx, cls_name in enumerate(PITCH_CLASSES):
        count = counts.get(cls_name, 1)
        if mode == "inverse":
            weights[idx] = total / (n_classes * count)
        elif mode == "sqrt_inverse":
            weights[idx] = np.sqrt(total / (n_classes * count))
        elif mode == "uniform":
            weights[idx] = 1.0

    return weights


def make_criterion(loss_name, class_weights, device, **kwargs):
    """Build the loss function."""
    if loss_name == "focal":
        gamma = kwargs.get("gamma", 2.0)
        use_alpha = kwargs.get("use_alpha", False)
        alpha = class_weights.to(device) if use_alpha else None
        return FocalLoss(gamma=gamma, alpha=alpha)
    elif loss_name == "weighted_ce":
        w = class_weights.to(device)
        return nn.CrossEntropyLoss(weight=w)
    elif loss_name == "weighted_ce_sqrt":
        sqrt_w = kwargs.get("sqrt_weights").to(device)
        return nn.CrossEntropyLoss(weight=sqrt_w)
    elif loss_name == "baseline_ce":
        return nn.CrossEntropyLoss(label_smoothing=0.1)
    else:
        raise ValueError(f"Unknown loss: {loss_name}")


def train_with_loss(loss_name, max_epochs=50, patience=10, batch_size=64, lr=3e-4,
                    preloaded_data=None, **loss_kwargs):
    """Train PitchGPT with a specific loss function."""
    t_start = time.time()

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    if preloaded_data is not None:
        splits = preloaded_data["splits"]
        pitcher_vocab = preloaded_data["pitcher_vocab"]
        config = preloaded_data["config"]
        train_ctx_t = preloaded_data["train_ctx_t"]
        train_pitch_t = preloaded_data["train_pitch_t"]
        train_pidx_t = preloaded_data["train_pidx_t"]
        val_ctx_t = preloaded_data["val_ctx_t"]
        val_pitch_t = preloaded_data["val_pitch_t"]
        val_pidx_t = preloaded_data["val_pidx_t"]
    else:
        df = load_all_data()
        splits = make_splits(df)
        pitcher_vocab = build_pitcher_vocab(splits["train"])
        config = PitchGPTConfig(n_pitchers=len(pitcher_vocab) + 1)
        train_ctx, train_pitch, train_pidx = extract_sequences(splits["train"], config.seq_len, pitcher_vocab)
        val_ctx, val_pitch, val_pidx = extract_sequences(splits["val"], config.seq_len, pitcher_vocab)
        train_ctx_t = torch.tensor(np.array(train_ctx), device=device)
        train_pitch_t = torch.tensor(np.array(train_pitch), device=device)
        train_pidx_t = torch.tensor(np.array(train_pidx), device=device)
        val_ctx_t = torch.tensor(np.array(val_ctx), device=device)
        val_pitch_t = torch.tensor(np.array(val_pitch), device=device)
        val_pidx_t = torch.tensor(np.array(val_pidx), device=device)

    model = PitchGPT(config).to(device)

    # Build loss function
    class_weights = compute_class_weights(splits["train"], mode="inverse")
    sqrt_weights = compute_class_weights(splits["train"], mode="sqrt_inverse")
    loss_kwargs["sqrt_weights"] = sqrt_weights

    criterion = make_criterion(loss_name, class_weights, device, **loss_kwargs)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.05)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)

    n_train = len(train_ctx_t)
    best_val_loss = float("inf")
    best_state = None
    epochs_without_improvement = 0

    for epoch in range(max_epochs):
        model.train()
        perm = torch.randperm(n_train, device=device)
        epoch_loss = 0.0
        n_batches = 0

        for batch_start in range(0, n_train, batch_size):
            idx = perm[batch_start:batch_start + batch_size]
            pitch_batch = train_pitch_t[idx]
            ctx_batch = train_ctx_t[idx]
            pidx_batch = train_pidx_t[idx]

            input_pitch = pitch_batch[:, :-1].clamp(min=0)
            input_ctx = ctx_batch[:, :-1]
            target = pitch_batch[:, 1:]

            logits = model(input_pitch, input_ctx, pidx_batch)

            mask = target >= 0
            loss = criterion(logits[mask], target[mask])

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        scheduler.step()

        # Validation (always use standard CE for comparable val_loss)
        model.eval()
        with torch.no_grad():
            val_input = val_pitch_t[:, :-1].clamp(min=0)
            val_ctx_in = val_ctx_t[:, :-1]
            val_target = val_pitch_t[:, 1:]
            val_logits = model(val_input, val_ctx_in, val_pidx_t)
            val_mask = val_target >= 0
            val_loss = F.cross_entropy(val_logits[val_mask], val_target[val_mask]).item()

        train_loss = epoch_loss / n_batches
        elapsed = time.time() - t_start

        if epoch % 5 == 0 or epoch == max_epochs - 1:
            print(f"  epoch {epoch+1:3d} | train_loss={train_loss:.4f} val_loss={val_loss:.4f} [{elapsed:.0f}s]")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"  Early stop at epoch {epoch+1}")
                break

    model.load_state_dict(best_state)
    model.eval()

    # Test set accuracy
    def make_predict_fn(m, cfg, dev, pvocab):
        def predict_fn(game_df):
            n = len(game_df)
            predictions = [PITCH_CLASSES[0]]
            pitch_ids = []
            ctx_data = []
            pitcher_id_raw = int(game_df["pitcher"].iloc[0]) if "pitcher" in game_df.columns else 0
            pitcher_idx = pvocab.get(pitcher_id_raw, 0)
            pitcher_t = torch.tensor([pitcher_idx], device=dev)

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

                seq_len = min(len(pitch_ids), cfg.seq_len)
                p_tensor = torch.tensor([pitch_ids[-seq_len:]], device=dev)
                c_tensor = torch.tensor([ctx_data[-seq_len:]], device=dev)

                with torch.no_grad():
                    logits = m(p_tensor, c_tensor, pitcher_t)
                    pred_idx = logits[0, -1].argmax().item()
                    predictions.append(PITCH_CLASSES[pred_idx])
            return predictions
        return predict_fn

    predict_fn = make_predict_fn(model, config, device, pitcher_vocab)

    test_df = splits["test"]
    all_preds = []
    all_actuals = []
    for game_df in iter_games(test_df):
        preds = predict_fn(game_df)
        actuals = game_df["pitch_type_simplified"].tolist()
        all_preds.extend(preds)
        all_actuals.extend(actuals)

    total = len(all_preds)
    correct = sum(p == a for p, a in zip(all_preds, all_actuals))
    accuracy = correct / total

    pred_dist = Counter(all_preds)
    per_class = {}
    for cls in PITCH_CLASSES:
        cls_idx = [i for i, a in enumerate(all_actuals) if a == cls]
        if cls_idx:
            per_class[cls] = sum(all_preds[i] == all_actuals[i] for i in cls_idx) / len(cls_idx)

    training_time = time.time() - t_start
    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "pred_dist": {k: v / total for k, v in pred_dist.items()},
        "val_loss": best_val_loss,
        "training_time": training_time,
    }


def preload_data():
    """Load data and tensors once, reuse across experiments."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    print(f"Device: {device}")
    print("Loading data (one-time)...")
    df = load_all_data()
    splits = make_splits(df)
    pitcher_vocab = build_pitcher_vocab(splits["train"])
    config = PitchGPTConfig(n_pitchers=len(pitcher_vocab) + 1)

    print("Extracting sequences...")
    train_ctx, train_pitch, train_pidx = extract_sequences(splits["train"], config.seq_len, pitcher_vocab)
    val_ctx, val_pitch, val_pidx = extract_sequences(splits["val"], config.seq_len, pitcher_vocab)

    print("Converting to tensors...")
    data = {
        "splits": splits,
        "pitcher_vocab": pitcher_vocab,
        "config": config,
        "train_ctx_t": torch.tensor(np.array(train_ctx), device=device),
        "train_pitch_t": torch.tensor(np.array(train_pitch), device=device),
        "train_pidx_t": torch.tensor(np.array(train_pidx), device=device),
        "val_ctx_t": torch.tensor(np.array(val_ctx), device=device),
        "val_pitch_t": torch.tensor(np.array(val_pitch), device=device),
        "val_pidx_t": torch.tensor(np.array(val_pidx), device=device),
    }

    # Class distribution
    counts = splits["train"]["pitch_type_simplified"].value_counts()
    total = len(splits["train"])
    print(f"Train class dist: {', '.join(f'{c}={counts.get(c, 0)/total*100:.1f}%' for c in PITCH_CLASSES)}")
    print(f"Train: {len(train_ctx)} seqs | Val: {len(val_ctx)} seqs")
    print("Data ready.\n")

    return data


def main():
    data = preload_data()

    experiments = [
        ("focal g=2.0", "focal", {"gamma": 2.0}),
        ("weighted CE (inv)", "weighted_ce", {}),
    ]

    print(f"{'Experiment':<25} {'Acc':>7} {'VLoss':>7} {'Fast%':>6} {'Brk%':>6} {'Off%':>6} | {'acc_f':>6} {'acc_b':>6} {'acc_o':>6} {'Time':>5}")
    print("-" * 100)

    all_results = []
    for name, loss_name, kwargs in experiments:
        print(f"\n>>> Training: {name}")
        result = train_with_loss(loss_name, preloaded_data=data, **kwargs)

        pf = result["pred_dist"].get("fast", 0) * 100
        pb = result["pred_dist"].get("breaking", 0) * 100
        po = result["pred_dist"].get("off-speed", 0) * 100
        af = result["per_class"].get("fast", 0)
        ab = result["per_class"].get("breaking", 0)
        ao = result["per_class"].get("off-speed", 0)
        t = result["training_time"]

        line = f"{name:<25} {result['accuracy']:>7.4f} {result['val_loss']:>7.4f} {pf:>5.1f}% {pb:>5.1f}% {po:>5.1f}% | {af:>6.4f} {ab:>6.4f} {ao:>6.4f} {t:>4.0f}s"
        print(f"RESULT: {line}")
        all_results.append((name, result))

    print("\n\n=== SUMMARY ===")
    print(f"{'Experiment':<25} {'Acc':>7} {'VLoss':>7} {'Fast%':>6} {'Brk%':>6} {'Off%':>6} | {'acc_f':>6} {'acc_b':>6} {'acc_o':>6}")
    print("-" * 95)
    for name, result in all_results:
        pf = result["pred_dist"].get("fast", 0) * 100
        pb = result["pred_dist"].get("breaking", 0) * 100
        po = result["pred_dist"].get("off-speed", 0) * 100
        af = result["per_class"].get("fast", 0)
        ab = result["per_class"].get("breaking", 0)
        ao = result["per_class"].get("off-speed", 0)
        print(f"{name:<25} {result['accuracy']:>7.4f} {result['val_loss']:>7.4f} {pf:>5.1f}% {pb:>5.1f}% {po:>5.1f}% | {af:>6.4f} {ab:>6.4f} {ao:>6.4f}")

    best_name, best_result = max(all_results, key=lambda x: x[1]["accuracy"])
    print(f"\nBest: {best_name} with accuracy={best_result['accuracy']:.4f}")


if __name__ == "__main__":
    main()
