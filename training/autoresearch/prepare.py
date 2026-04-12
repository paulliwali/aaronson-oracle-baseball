"""
Fixed data preparation and evaluation for autoresearch experiments.
Wraps the shared harness with a fixed time budget.

DO NOT MODIFY — this is the fixed evaluation harness for autoresearch.
"""

import sys
from pathlib import Path

# Add training/ to path so we can import the shared prepare module
_training_dir = str(Path(__file__).parent.parent)
if _training_dir not in sys.path:
    sys.path.insert(0, _training_dir)

# Re-export everything from the shared harness
from prepare import (  # noqa: F401, E402
    PITCH_CLASSES,
    PITCH_TO_IDX,
    NUM_CLASSES,
    SEED,
    DATA_DIR,
    MODELS_DIR,
    HISTORY_LEN,
    NUM_FEATURES,
    load_all_data,
    make_splits,
    iter_games,
    encode_pitch,
    decode_pitch,
    extract_game_features,
    extract_all_features,
    extract_sequences,
    build_pitcher_vocab,
    evaluate,
)

# Autoresearch-specific constraint
TIME_BUDGET = 300  # training time budget in seconds (5 minutes)
