"""
Train a production pitch prediction model.

Usage:
    uv run python training/train.py transformer
    uv run python training/train.py tree
"""

import sys


MODELS = {
    "transformer": "models.transformer",
    "tree": "models.tree",
    "naive": "models.naive",
    "ngram": "models.ngram",
    "frequency": "models.frequency",
    "markov": "models.markov",
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MODELS:
        print(f"Usage: python training/train.py <model>")
        print(f"Available models: {', '.join(MODELS)}")
        sys.exit(1)

    model_name = sys.argv[1]
    print(f"Training: {model_name}")
    print("=" * 60)

    # Import and run the model's train function
    import importlib
    module = importlib.import_module(MODELS[model_name])
    module.train()


if __name__ == "__main__":
    main()
