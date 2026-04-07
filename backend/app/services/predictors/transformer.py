"""Small causal transformer predictor for pitch sequences."""

from pathlib import Path
from typing import List

import pandas as pd

from .base import BasePredictorModel, DEFAULT_PITCH_VALUE, PITCH_CLASSES, PITCH_TO_IDX, MODELS_DIR


class TransformerPredictor(BasePredictorModel):
    """Loads a trained PitchGPT model from training/train.py. Requires trained weights."""

    def __init__(self):
        super().__init__("Transformer")
        self._model = None
        self._config = None
        self._device = None
        self._load_attempted = False

    def _load_model(self):
        if self._load_attempted:
            return
        self._load_attempted = True
        model_path = MODELS_DIR / "pitch_transformer.pt"
        if not model_path.exists():
            return

        import sys

        import torch

        training_dir = str(Path(__file__).parent.parent.parent.parent.parent / "training")
        if training_dir not in sys.path:
            sys.path.insert(0, training_dir)
        from train import PitchGPT, PitchGPTConfig

        if torch.cuda.is_available():
            self._device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            self._device = torch.device("mps")
        else:
            self._device = torch.device("cpu")

        # PitchGPTConfig was pickled under __main__ / __mp_main__ — inject the
        # class into whichever module name the unpickler will look up.
        for mod_name in ("__main__", "__mp_main__"):
            mod = sys.modules.get(mod_name)
            if mod is not None and not hasattr(mod, "PitchGPTConfig"):
                setattr(mod, "PitchGPTConfig", PitchGPTConfig)

        checkpoint = torch.load(model_path, map_location=self._device, weights_only=False)

        self._config = checkpoint["config"]
        self._model = PitchGPT(self._config).to(self._device)
        self._model.load_state_dict(checkpoint["model_state_dict"])
        self._model.eval()

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        self._load_model()
        if self._model is None:
            return [DEFAULT_PITCH_VALUE] * len(game_stats_df)

        import torch

        n = len(game_stats_df)
        predictions = [DEFAULT_PITCH_VALUE]  # can't predict first pitch

        pitch_ids = []
        ctx_data = []

        for i in range(n):
            row = game_stats_df.iloc[i]
            pitch_ids.append(PITCH_TO_IDX.get(row["pitch_type_simplified"], 0))

            balls = int(row.get("balls", 0))
            strikes = int(row.get("strikes", 0))
            outs = int(row.get("outs_when_up", 0))
            inning = min(int(row.get("inning", 1)), 12)
            stand = 0 if str(row.get("stand", "R")) == "L" else 1
            phand = 0 if str(row.get("p_throws", "R")) == "L" else 1
            ctx_data.append([balls, strikes, outs, inning, stand, phand])

            if i == 0:
                continue

            seq_len = min(len(pitch_ids), self._config.seq_len)
            p_tensor = torch.tensor([pitch_ids[-seq_len:]], device=self._device)
            c_tensor = torch.tensor([ctx_data[-seq_len:]], device=self._device)

            with torch.no_grad():
                logits = self._model(p_tensor, c_tensor)
                pred_idx = logits[0, -1].argmax().item()
                predictions.append(PITCH_CLASSES[pred_idx])

        return predictions
