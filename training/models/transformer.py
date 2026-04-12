"""PitchGPT: Causal transformer for pitch sequence prediction.

Architecture: 6-layer transformer with per-pitch context embeddings,
pitcher identity embeddings, and causal attention masking.
"""

import time
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

import sys
from pathlib import Path

_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

from prepare import (
    PITCH_CLASSES,
    NUM_CLASSES,
    MODELS_DIR,
    load_all_data,
    make_splits,
    extract_sequences,
    evaluate,
    encode_pitch,
    build_pitcher_vocab,
)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class PitchGPTConfig:
    seq_len: int = 256
    n_layers: int = 6
    n_heads: int = 4
    d_model: int = 128
    dropout: float = 0.25
    n_pitch_types: int = NUM_CLASSES
    n_balls: int = 4
    n_strikes: int = 3
    n_outs: int = 3
    n_innings: int = 13
    n_stand: int = 2
    n_phand: int = 2
    n_pitchers: int = 64


class PitchGPT(nn.Module):
    def __init__(self, config: PitchGPTConfig):
        super().__init__()
        self.config = config
        d = config.d_model
        e = d // 4

        self.pitch_embed = nn.Embedding(config.n_pitch_types, d)
        self.balls_embed = nn.Embedding(config.n_balls, e)
        self.strikes_embed = nn.Embedding(config.n_strikes, e)
        self.outs_embed = nn.Embedding(config.n_outs, e)
        self.inning_embed = nn.Embedding(config.n_innings, e)
        self.stand_embed = nn.Embedding(config.n_stand, e)
        self.phand_embed = nn.Embedding(config.n_phand, e)
        self.ctx_proj = nn.Linear(6 * e, d)
        self.pos_embed = nn.Embedding(config.seq_len, d)
        self.pitcher_embed = nn.Embedding(config.n_pitchers, d)

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

    def forward(self, pitch_ids, context, pitcher_ids=None):
        B, T = pitch_ids.shape
        device = pitch_ids.device

        x = self.pitch_embed(pitch_ids)
        if pitcher_ids is None:
            pitcher_ids = torch.zeros(B, dtype=torch.long, device=device)
        pitcher_vec = self.pitcher_embed(pitcher_ids.clamp(0, self.config.n_pitchers - 1))
        x = x + pitcher_vec.unsqueeze(1)

        balls = context[:, :, 0].clamp(0, 3)
        strikes = context[:, :, 1].clamp(0, 2)
        outs = context[:, :, 2].clamp(0, 2)
        innings = context[:, :, 3].clamp(1, 12)
        stand = context[:, :, 4].clamp(0, 1)
        phand = context[:, :, 5].clamp(0, 1)

        ctx = torch.cat([
            self.balls_embed(balls),
            self.strikes_embed(strikes),
            self.outs_embed(outs),
            self.inning_embed(innings),
            self.stand_embed(stand),
            self.phand_embed(phand),
        ], dim=-1)
        x = x + self.ctx_proj(ctx)

        pos = torch.arange(T, device=device)
        x = x + self.pos_embed(pos)

        causal_mask = nn.Transformer.generate_square_subsequent_mask(T, device=device)
        x = self.transformer(x, mask=causal_mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


# ---------------------------------------------------------------------------
# Inference helper
# ---------------------------------------------------------------------------

def make_predict_fn(model, config, device, pitcher_vocab):
    """Create a predict_fn compatible with prepare.evaluate()."""
    model.eval()

    def predict_fn(game_df):
        n = len(game_df)
        predictions = [PITCH_CLASSES[0]]

        pitch_ids = []
        ctx_data = []
        pitcher_id_raw = int(game_df["pitcher"].iloc[0]) if "pitcher" in game_df.columns else 0
        pitcher_idx = pitcher_vocab.get(pitcher_id_raw, 0)
        pitcher_t = torch.tensor([pitcher_idx], device=device)

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
                pred_idx = logits[0, -1].argmax().item()
                predictions.append(PITCH_CLASSES[pred_idx])

        return predictions

    return predict_fn


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(max_epochs: int = 50, patience: int = 10, batch_size: int = 64, lr: float = 3e-4):
    """Train PitchGPT to convergence. No time budget -- runs until early stop."""
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

    pitcher_vocab = build_pitcher_vocab(splits["train"])
    print(f"Pitcher vocab: {len(pitcher_vocab)} pitchers (+ 1 unknown slot)")

    config = PitchGPTConfig(n_pitchers=len(pitcher_vocab) + 1)

    print("Extracting sequences...")
    train_ctx, train_pitch, train_pidx = extract_sequences(splits["train"], config.seq_len, pitcher_vocab)
    val_ctx, val_pitch, val_pidx = extract_sequences(splits["val"], config.seq_len, pitcher_vocab)
    print(f"Train: {len(train_ctx)} games | Val: {len(val_ctx)} games")

    # Convert to tensors
    train_ctx_t = torch.tensor(np.array(train_ctx), device=device)
    train_pitch_t = torch.tensor(np.array(train_pitch), device=device)
    train_pidx_t = torch.tensor(np.array(train_pidx), device=device)
    val_ctx_t = torch.tensor(np.array(val_ctx), device=device)
    val_pitch_t = torch.tensor(np.array(val_pitch), device=device)
    val_pidx_t = torch.tensor(np.array(val_pidx), device=device)

    data_time = time.time() - t_start
    print(f"Data loading took {data_time:.0f}s")

    # Model
    model = PitchGPT(config).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.05)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs)

    # Training loop
    n_train = len(train_ctx_t)
    best_val_loss = float("inf")
    best_state = None
    epochs_without_improvement = 0

    print(f"\nTraining (max {max_epochs} epochs, patience {patience})...")
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
            loss = F.cross_entropy(
                logits[mask],
                target[mask],
                label_smoothing=0.1,
            )

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            n_batches += 1

        scheduler.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_input = val_pitch_t[:, :-1].clamp(min=0)
            val_ctx_in = val_ctx_t[:, :-1]
            val_target = val_pitch_t[:, 1:]
            val_logits = model(val_input, val_ctx_in, val_pidx_t)
            val_mask = val_target >= 0
            val_loss = F.cross_entropy(val_logits[val_mask], val_target[val_mask]).item()

        elapsed = time.time() - t_start
        train_loss = epoch_loss / n_batches
        print(f"  epoch {epoch+1:3d} | train_loss={train_loss:.4f} val_loss={val_loss:.4f} lr={optimizer.param_groups[0]['lr']:.2e} [{elapsed:.0f}s]")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"  Early stop: no val improvement for {patience} epochs")
                break

    total_training_time = time.time() - t_start

    # Restore best model
    model.load_state_dict(best_state)
    model.eval()

    # Save
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "pitch_transformer.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": config,
        "pitcher_vocab": pitcher_vocab,
    }, model_path)
    print(f"\nSaved to {model_path}")

    # Evaluate
    print("Evaluating on test set...")
    predict_fn = make_predict_fn(model, config, device, pitcher_vocab)
    results = evaluate(predict_fn, split="test")

    print("---")
    print(f"test_accuracy:    {results['accuracy']:.6f}")
    print(f"val_loss:         {best_val_loss:.6f}")
    print(f"training_seconds: {total_training_time:.1f}")
    print(f"epochs:           {epoch+1}")
    print(f"num_params:       {n_params}")
    print(f"n_pitches:        {results['n_pitches']}")
    print(f"n_games:          {results['n_games']}")
    for cls, acc in results["per_class"].items():
        print(f"acc_{cls}: {acc:.6f}")

    return results
