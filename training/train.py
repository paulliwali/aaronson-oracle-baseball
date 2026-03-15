"""
Pitch prediction model training. This is the file you modify.
Architecture, optimizer, hyperparameters, model type — everything is fair game.

Usage: uv run python training/train.py
"""

import time
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from prepare import (
    TIME_BUDGET,
    PITCH_CLASSES,
    NUM_CLASSES,
    MODELS_DIR,
    load_all_data,
    make_splits,
    extract_sequences,
    evaluate,
    encode_pitch,
    iter_games,
)


@dataclass
class PitchGPTConfig:
    seq_len: int = 256
    n_layers: int = 6
    n_heads: int = 4
    d_model: int = 128
    dropout: float = 0.15
    n_pitch_types: int = NUM_CLASSES
    n_balls: int = 4
    n_strikes: int = 3
    n_outs: int = 3
    n_innings: int = 13


class PitchGPT(nn.Module):
    def __init__(self, config: PitchGPTConfig):
        super().__init__()
        self.config = config
        d = config.d_model

        self.pitch_embed = nn.Embedding(config.n_pitch_types, d)
        self.balls_embed = nn.Embedding(config.n_balls, d // 4)
        self.strikes_embed = nn.Embedding(config.n_strikes, d // 4)
        self.outs_embed = nn.Embedding(config.n_outs, d // 4)
        self.inning_embed = nn.Embedding(config.n_innings, d // 4)
        self.ctx_proj = nn.Linear(d, d)
        self.pos_embed = nn.Embedding(config.seq_len, d)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d,
            nhead=config.n_heads,
            dim_feedforward=d * 6,
            dropout=config.dropout,
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.n_layers)
        self.ln_f = nn.LayerNorm(d)
        self.head = nn.Linear(d, config.n_pitch_types)

    def forward(self, pitch_ids, context):
        B, T = pitch_ids.shape
        device = pitch_ids.device

        x = self.pitch_embed(pitch_ids)

        balls = context[:, :, 0].clamp(0, 3)
        strikes = context[:, :, 1].clamp(0, 2)
        outs = context[:, :, 2].clamp(0, 2)
        innings = context[:, :, 3].clamp(1, 12)

        ctx = torch.cat([
            self.balls_embed(balls),
            self.strikes_embed(strikes),
            self.outs_embed(outs),
            self.inning_embed(innings),
        ], dim=-1)
        x = x + self.ctx_proj(ctx)

        pos = torch.arange(T, device=device)
        x = x + self.pos_embed(pos)

        causal_mask = nn.Transformer.generate_square_subsequent_mask(T, device=device)
        x = self.transformer(x, mask=causal_mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def make_predict_fn(model, config, device):
    """Create a predict_fn compatible with prepare.evaluate()."""
    model.eval()

    def predict_fn(game_df):
        n = len(game_df)
        predictions = [PITCH_CLASSES[0]]  # can't predict first pitch

        pitch_ids = []
        ctx_data = []

        for i in range(n):
            row = game_df.iloc[i]
            pitch_ids.append(encode_pitch(row["pitch_type_simplified"]))
            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))
            inning = min(int(row.get("inning", 1)), 12)
            ctx_data.append([balls, strikes, outs, inning])

            if i == 0:
                continue

            seq_len = min(len(pitch_ids), config.seq_len)
            p_tensor = torch.tensor([pitch_ids[-seq_len:]], device=device)
            c_tensor = torch.tensor([ctx_data[-seq_len:]], device=device)

            with torch.no_grad():
                logits = model(p_tensor, c_tensor)
                pred_idx = logits[0, -1].argmax().item()
                predictions.append(PITCH_CLASSES[pred_idx])

        return predictions

    return predict_fn


def main():
    t_start = time.time()

    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Device: {device}")

    # Data
    print("Loading data...")
    df = load_all_data()
    splits = make_splits(df)
    print(f"Train: {len(splits['train']):,} | Val: {len(splits['val']):,} | Test: {len(splits['test']):,}")

    config = PitchGPTConfig()

    print("Extracting sequences...")
    train_ctx, train_pitch = extract_sequences(splits["train"], config.seq_len)
    val_ctx, val_pitch = extract_sequences(splits["val"], config.seq_len)
    print(f"Train: {len(train_ctx)} games | Val: {len(val_ctx)} games")

    # Convert to tensors
    train_ctx_t = torch.tensor(np.array(train_ctx), device=device)
    train_pitch_t = torch.tensor(np.array(train_pitch), device=device)
    val_ctx_t = torch.tensor(np.array(val_ctx), device=device)
    val_pitch_t = torch.tensor(np.array(val_pitch), device=device)

    # Model
    model = PitchGPT(config).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=TIME_BUDGET)

    # Training loop
    batch_size = 32
    n_train = len(train_ctx_t)
    best_val_loss = float("inf")
    step = 0

    print(f"\nTraining for {TIME_BUDGET}s...")
    while time.time() - t_start < TIME_BUDGET:
        model.train()
        perm = torch.randperm(n_train, device=device)

        for batch_start in range(0, n_train, batch_size):
            if time.time() - t_start >= TIME_BUDGET:
                break

            idx = perm[batch_start:batch_start + batch_size]
            pitch_batch = train_pitch_t[idx]
            ctx_batch = train_ctx_t[idx]

            # Shift: input is pitches[:-1], target is pitches[1:]
            input_pitch = pitch_batch[:, :-1].clamp(min=0)
            input_ctx = ctx_batch[:, :-1]
            target = pitch_batch[:, 1:]

            logits = model(input_pitch, input_ctx)

            # Mask padded positions (target == -1)
            mask = target >= 0
            loss = F.cross_entropy(
                logits[mask],
                target[mask],
            )

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            step += 1

        scheduler.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_input = val_pitch_t[:, :-1].clamp(min=0)
            val_ctx_in = val_ctx_t[:, :-1]
            val_target = val_pitch_t[:, 1:]
            val_logits = model(val_input, val_ctx_in)
            val_mask = val_target >= 0
            val_loss = F.cross_entropy(val_logits[val_mask], val_target[val_mask]).item()

        elapsed = time.time() - t_start
        print(f"  [{elapsed:5.0f}s] step={step:5d} val_loss={val_loss:.4f} lr={optimizer.param_groups[0]['lr']:.2e}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    total_training_time = time.time() - t_start

    # Restore best model
    model.load_state_dict(best_state)
    model.eval()

    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "pitch_transformer.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": config,
    }, model_path)

    # Evaluate
    print("\nEvaluating on test set...")
    predict_fn = make_predict_fn(model, config, device)
    results = evaluate(predict_fn, split="test")

    # Print results
    t_end = time.time()
    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"val_loss:         {best_val_loss:.6f}")
    print(f"training_seconds: {total_training_time:.1f}")
    print(f"total_seconds:    {t_end - t_start:.1f}")
    print(f"total_steps:      {step}")
    print(f"num_params:       {n_params}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")


if __name__ == "__main__":
    main()
