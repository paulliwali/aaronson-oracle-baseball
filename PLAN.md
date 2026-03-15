# Plan: Improve Pitch Prediction Models

## Status: Phase 1 in progress

## Goal

Use the autoresearch methodology to autonomously discover the best pitch prediction model. Instead of hand-picking architectures, we set up a fixed evaluation harness and let the experiment loop explore the space.

## Completed

### Infrastructure
- [x] Training pipeline with autoresearch pattern (`training/`)
- [x] `prepare.py` — fixed evaluation harness, data loading, splits, feature extraction (read-only)
- [x] `train.py` — mutable model file (starts with PitchGPT transformer baseline)
- [x] `program.md` — experiment protocol for autonomous Claude sessions
- [x] `download_starters.py` — bulk Statcast data download (25 pitchers, 2022-2024)
- [x] `benchmark.py` — benchmark app models against test split
- [x] `pitchers.json` — curated list of ~25 top MLB starters
- [x] New predictor classes in `predictors.py`: MarkovContext, TreePredictor, TransformerPredictor
- [x] Dependencies: `scikit-learn`, `torch`, `joblib` in `[project.optional-dependencies.training]`
- [x] uv for package management (`uv.lock` generated)
- [x] `.gitignore` for `data/training/`, `models/`, etc.

## Current Step

### Phase 1: Download Data
```bash
uv run python training/download_starters.py
```
Downloads ~25 pitchers x 3 seasons of Statcast data to `data/training/`. Rate-limited (5s between API calls), resumable (skips existing files), filters to starter appearances (>60 pitches per game).

## Next Steps

### Phase 2: Establish Baseline
```bash
uv run python training/prepare.py     # verify data
uv run python training/train.py       # run baseline (PitchGPT transformer, 5 min)
uv run python training/benchmark.py   # benchmark existing app models
```

### Phase 3: Autoresearch Loop
Start an autonomous Claude session:
> Read training/program.md and follow the experiment protocol. Run tag: mar14

Claude will:
1. Create branch `autoresearch/mar14`
2. Run baseline, record in `results.tsv`
3. Loop: modify `train.py` → commit → run → keep/revert → repeat
4. Try different approaches: tree models, MLPs, ensembles, different features, etc.
5. Continue until interrupted

### Phase 4: Integration
Once autoresearch finds a good model:
1. Best weights already saved to `models/`
2. Corresponding predictor class already in `predictors.py`
3. Restart backend — new models appear in API automatically
4. Frontend renders them in charts with no changes needed

## Architecture Decisions

### Why autoresearch over manual model selection
- Manual approach: we guess "use a transformer", spend time implementing, hope it works
- Autoresearch approach: fixed eval harness, autonomous exploration, data-driven model selection
- The loop can discover that a simple Random Forest beats a transformer — or that a hybrid approach works best

### Split strategy
Using **within-pitcher chronological** (70/15/15) as the primary split:
- Each pitcher's games sorted by date
- Tests temporal generalization (predicting future games from past)
- Every pitcher appears in all splits
- Most realistic: mirrors the app's use case

### Evaluation metric
**Test accuracy** on the within-pitcher split. Simple, interpretable, directly maps to what users see in the app.

### What prepare.py provides
- `load_all_data()` — all pitcher-season CSVs into one DataFrame
- `make_splits(df)` — deterministic train/val/test split
- `iter_games(df)` — yields individual game DataFrames
- `extract_all_features(df)` — tabular features (23 dims) for tree/MLP models
- `extract_sequences(df)` — sequential data for transformer/RNN models
- `evaluate(predict_fn)` — the ground truth metric (DO NOT MODIFY)
