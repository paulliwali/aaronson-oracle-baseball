# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack web application that adapts [Aaronson's Oracle](https://github.com/elsehow/aaronson-oracle/blob/master/README.md) algorithm to predict baseball pitches. It compares multiple prediction models to determine which algorithm best anticipates a pitcher's next pitch type.

The application uses:
- **Backend**: FastAPI (Python) for REST API
- **Frontend**: React + Vite for visualization
- **Data**: PyBaseball (Statcast API) for MLB pitch data
- **Database**: PostgreSQL for permanent storage of Statcast data
- **Caching**: Redis for fast access to recent queries
- **Training**: Autoresearch-style experiment loop for model improvement
- **Package management**: uv

Pitch types are simplified from Statcast's detailed categories into three groups: "fast", "breaking", and "off-speed" (see `data/pitch_map.json`).

## Development Commands

### Setup

```bash
uv sync                          # Install core dependencies
uv sync --extra training          # + scikit-learn, torch, joblib
uv sync --extra dev               # + pytest, black, ruff
uv sync --extra training --extra dev  # Everything
```

### Backend

```bash
cd backend && uv run python run.py
```
API at http://localhost:8000, docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend && npm install && npm run dev
```
App at http://localhost:5173

### Training

```bash
# 1. One-time: download Statcast data (~25 pitchers x 3 seasons)
uv run python training/download_starters.py

# 2. Verify data is ready
uv run python training/prepare.py

# 3. Train model (5-min time budget)
uv run python training/train.py

# 4. Benchmark all app models against test set
uv run python training/benchmark.py
```

### Autoresearch (autonomous model improvement)

Read `training/program.md` and follow the experiment protocol. This is an autonomous loop where Claude iteratively modifies `training/train.py`, runs experiments, keeps improvements, and reverts regressions. Each experiment has a fixed 5-minute time budget.

To start: `Read training/program.md and follow the experiment protocol. Run tag: <tag>`

## Architecture

### Backend Structure (FastAPI)

```
backend/
├── app/
│   ├── main.py           # FastAPI app, CORS, lifespan management
│   ├── models/
│   │   └── schemas.py    # Pydantic models for request/response validation
│   ├── routers/
│   │   ├── players.py    # Player endpoints (/api/players/*)
│   │   └── predictions.py # Prediction endpoints (/api/predictions/*)
│   └── services/
│       ├── baseball.py    # Statcast data fetching, caching, pitch mapping
│       └── predictors/    # One file per model (see below)
└── run.py                 # Uvicorn server entry point
```

### Training Infrastructure (autoresearch pattern)

```
training/                          # Experiment loop
├── program.md                     # Experiment protocol (read this first)
├── prepare.py                     # FIXED: data loading, splits, evaluation harness
├── train.py                       # MUTABLE: model architecture, optimizer, training loop
├── pitchers.json                  # Curated starter list (~25 pitchers)
├── download_starters.py           # Bulk Statcast data download
├── benchmark.py                   # Benchmark app models against test split
├── results.tsv                    # Experiment log (created during autoresearch)
└── run.log                        # Latest training output
data/training/                     # Downloaded CSVs (gitignored)
models/                            # Saved model weights (gitignored)
MODEL_CARD.md                      # Benchmark results documentation
```

Key design:
- `prepare.py` is **read-only**: fixed evaluation metric (`evaluate(predict_fn)`), data splits, feature extraction
- `train.py` is the **only file modified** during autoresearch: architecture, optimizer, hyperparameters, model type
- Each experiment runs for a fixed 5-minute time budget
- Results logged to `results.tsv`, improvements kept, regressions reverted

### Prediction Models (`backend/app/services/predictors/`)

Each model is in its own file. All inherit from `BasePredictorModel` and implement `predict(game_stats_df) -> List[str]`.

```
predictors/
├── __init__.py       # Registry (AVAILABLE_MODELS) — add new models here
├── base.py           # BasePredictorModel + shared constants
├── naive.py          # NaivePredictor — always predicts "fast"
├── ngram.py          # NGramPredictor — Aaronson Oracle (n=3)
├── markov.py         # MarkovContextPredictor — n-gram + count/outs context
├── tree.py           # TreePredictor — Random Forest (requires models/random_forest.joblib)
└── transformer.py    # TransformerPredictor — PitchGPT (requires models/pitch_transformer.pt)
```

To add a new model:
1. Create `predictors/<name>.py` with a class extending `BasePredictorModel`
2. If it needs trained weights, save to `models/` and check existence in `__init__.py`
3. Register in `_build_model_registry()` in `__init__.py`

### API Endpoints

- **GET** `/api/players/list` — hardcoded pitcher list
- **POST** `/api/players/stats` — player ID and game dates for 2023 season
- **POST** `/api/predictions/game` — predictions from all models for a specific game

### Data Flow

1. User selects pitcher → `/api/players/stats` → Statcast player ID + game dates
2. User selects game → `/api/predictions/game` → all models run predictions
3. Frontend renders charts comparing model accuracies

### 3-Tier Caching Strategy

`fetch_game_stats()` checks: **Postgres** (permanent) → **Redis** (1hr TTL) → **Statcast API** (source of truth), saving back down the chain.

### Frontend (React)

`ModelComparison` component displays game metadata, pitch distribution, prediction scatter plots, and rolling accuracy charts. Vibrant "Backyard Baseball" theme with Comic Sans.

## Deployment

### Single-Service Deployment (Railway)

FastAPI serves both the API and the React frontend (built via Dockerfile). Frontend at `/`, API at `/api/*`, docs at `/docs`.

Required env vars: `PORT`, `REDIS_URL`, `DATABASE_URL`.
