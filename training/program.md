# autoresearch: pitch prediction

This is an experiment to have the LLM do its own research on pitch prediction models.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar14`). The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current main.
3. **Read the in-scope files**: The training directory is small. Read these files for full context:
   - `training/program.md` — this file, the experiment protocol.
   - `training/prepare.py` — fixed constants, data loading, splits, feature extraction, evaluation. Do not modify.
   - `training/train.py` — the file you modify. Model architecture, optimizer, training loop.
4. **Verify data exists**: Check that `data/training/` contains CSV files. If not, tell the human to run `uv run python training/download_starters.py`.
5. **Initialize results.tsv**: Create `training/results.tsv` with just the header row. The baseline will be recorded after the first run.
6. **Confirm and go**: Confirm setup looks good.

Once you get confirmation, kick off the experimentation.

## Problem context

We are predicting the simplified pitch type (fast / breaking / off-speed) for MLB starting pitchers. The data comes from Statcast and is organized by game. Each game is a sequence of 60-120+ pitches with contextual features (count, outs, inning, score).

Key constraints:
- Only 3 classes, heavily imbalanced (~55% fast, ~25% breaking, ~20% off-speed)
- Pitchers have individual tendencies — what works for one may not work for another
- Game-level sequential structure matters (pitchers establish patterns within a game)
- The model must implement `predict_fn(game_df) -> List[str]` for the evaluation harness

## Experimentation

Each experiment runs on a single machine. The training script runs for a **fixed time budget of 5 minutes** (wall clock). You launch it simply as: `uv run python training/train.py`.

**What you CAN do:**
- Modify `training/train.py` — this is the only file you edit. Everything is fair game: model architecture, optimizer, hyperparameters, training loop, model type (neural, tree, statistical), feature engineering, etc.

**What you CANNOT do:**
- Modify `training/prepare.py`. It is read-only. It contains the fixed evaluation, data loading, splits, and constants.
- Install new packages or add dependencies.
- Modify the evaluation harness. The `evaluate()` function in `prepare.py` is the ground truth metric.

**The goal is simple: get the highest test_accuracy.** Since the time budget is fixed, you don't need to worry about training time — it's always 5 minutes. Everything is fair game: change the architecture, the optimizer, the hyperparameters, the model type entirely. The only constraint is that the code runs without crashing and finishes within the time budget.

**Available packages** (already in pyproject.toml):
- `torch` — neural network models
- `scikit-learn` — tree models, SVMs, etc.
- `numpy`, `pandas` — data manipulation
- Standard library (collections, pickle, etc.)

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome. When evaluating whether to keep a change, weigh the complexity cost against the improvement magnitude.

**The first run**: Your very first run should always be to establish the baseline, so you will run the training script as is.

## Output format

Once the script finishes it prints a summary like this:

```
---
test_accuracy:    0.543210
val_loss:         1.012345
training_seconds: 300.1
total_seconds:    325.9
total_steps:      1500
num_params:       12345
n_pitches:        45678
n_games:          234
acc_fast:         0.712345
acc_breaking:     0.345678
acc_off-speed:    0.234567
```

You can extract the key metric from the log file:

```
grep "^test_accuracy:" run.log
```

## Logging results

When an experiment is done, log it to `training/results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 5 columns:

```
commit	test_accuracy	status	description
```

1. git commit hash (short, 7 chars)
2. test_accuracy achieved (e.g. 0.543210) — use 0.000000 for crashes
3. status: `keep`, `discard`, or `crash`
4. short text description of what this experiment tried

Example:

```
commit	test_accuracy	status	description
a1b2c3d	0.543210	keep	baseline (PitchGPT transformer)
b2c3d4e	0.567890	keep	switch to Random Forest
c3d4e5f	0.534000	discard	double embedding dim
d4e5f6g	0.000000	crash	add rotary embeddings (OOM)
```

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/mar14`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on
2. Tune `training/train.py` with an experimental idea by directly hacking the code.
3. git commit
4. Run the experiment: `uv run python training/train.py > training/run.log 2>&1`
5. Read out the results: `grep "^test_accuracy:\|^val_loss:" training/run.log`
6. If the grep output is empty, the run crashed. Run `tail -n 50 training/run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after more than a few attempts, give up.
7. Record the results in the tsv
8. If test_accuracy improved (higher), you "advance" the branch, keeping the git commit
9. If test_accuracy is equal or worse, you git reset back to where you started

The idea is that you are a completely autonomous researcher trying things out. If they work, keep. If they don't, discard. And you're advancing the branch so that you can iterate.

**Timeout**: Each experiment should take ~5 minutes total (+ a few seconds for startup and eval overhead). If a run exceeds 10 minutes, kill it and treat it as a failure.

**Crashes**: If a run crashes, use your judgment: if it's something dumb and easy to fix (e.g. a typo), fix it and re-run. If the idea itself is fundamentally broken, just skip it, log "crash", and move on.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The human might be away and expects you to continue working *indefinitely* until manually stopped. You are autonomous. If you run out of ideas, think harder — try combining previous near-misses, try more radical changes, try entirely different model families. The loop runs until the human interrupts you.

## Ideas to explore

Some starting directions (you are not limited to these):

- **Model type**: The baseline is a small transformer. Try Random Forest, gradient boosting, or a simple MLP. Tree models often beat neural nets on tabular data with <100K samples.
- **Feature engineering**: The feature set in `prepare.py` is available via `extract_all_features()`. You can also build your own features directly from the game DataFrame.
- **Ensemble**: Combine multiple models (e.g. tree + neural) by averaging predictions or stacking.
- **Sequence modeling**: The transformer processes pitch sequences causally. Try different context lengths, attention patterns, or hybrid approaches.
- **Online learning**: Models that adapt during the game (like the existing N-gram) can be combined with pre-trained models.
- **Per-pitcher specialization**: If enough data exists per pitcher, consider pitcher-specific models or embeddings.

## Saving models for the app

When you achieve a new best test_accuracy, the model weights are saved to `models/pitch_transformer.pt` (or whatever format makes sense). The predictors in `backend/app/services/predictors.py` load these weights at runtime. Make sure the saved format is compatible with the predictor class.
