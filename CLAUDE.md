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

Pitch types are simplified from Statcast's detailed categories into three groups: "fast", "breaking", and "off-speed" (see `data/pitch_map.json`).

## Development Commands

### Backend

Install dependencies:
```bash
pip install -e .          # Install package
pip install -e ".[dev]"   # Install with dev dependencies
```

Run the FastAPI server:
```bash
cd backend
python3 run.py
```
The API will be available at http://localhost:8000 with interactive docs at http://localhost:8000/docs

**Note**: Use `python3` instead of `python` on macOS/Linux.

### Frontend

Install dependencies:
```bash
cd frontend
npm install
```

Run the development server:
```bash
npm run dev
```
The app will be available at http://localhost:5173

Build for production:
```bash
npm run build
```

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
│       └── predictors.py  # All prediction model implementations
└── run.py                 # Uvicorn server entry point
```

### Prediction Models (backend/app/services/predictors.py)

All models inherit from `BasePredictorModel` and implement:
- `predict()`: Generate predictions for all pitches in a game
- `calculate_accuracy()`: Overall accuracy metric
- `calculate_rolling_accuracy()`: Pitch-by-pitch accuracy progression

Available models in `AVAILABLE_MODELS`:
1. **NaivePredictor**: Always predicts "fast" (baseline)
2. **NGramPredictor**: Aaronson Oracle algorithm with configurable n-gram size (n=2,3,4)
3. **FrequencyPredictor**: Predicts based on running frequency distribution

To add a new model:
1. Create a class extending `BasePredictorModel`
2. Implement the `predict()` method
3. Add instance to `AVAILABLE_MODELS` list

### API Endpoints

**GET** `/api/players/list`
- Returns hardcoded list of pitchers

**POST** `/api/players/stats`
- Body: `{"player_name": "Logan Webb"}`
- Returns: Player ID and all game dates in 2023 season

**POST** `/api/predictions/game`
- Body: `{"player_name": "Logan Webb", "game_date": "2023-05-15"}`
- Returns: Performance metrics for all models on that specific game, including:
  - `home_team`: Home team abbreviation (e.g., "SF")
  - `away_team`: Away team abbreviation (e.g., "LAD")
  - `pitcher_team`: Pitcher's team (determined from `inning_topbot` field)
  - `total_pitches`: Number of pitches thrown
  - `pitch_types_distribution`: Count of each pitch type
  - `actual_pitches`: List of actual pitch types thrown
  - `models`: Array of model performance data

### Frontend Structure (React)

```
frontend/src/
├── App.jsx                      # Main app, state management, API calls
├── App.css                      # Global styles
└── components/
    ├── PlayerSelector.jsx       # Pitcher dropdown
    ├── GameSelector.jsx         # Game date dropdown
    └── ModelComparison.jsx      # Results visualization with Recharts
```

The `ModelComparison` component displays:
- Game metadata (pitcher with team affiliation, date, home vs away matchup, total pitches)
- Pitch type distribution (fast, breaking, off-speed)
- Scatter plot showing pitch predictions vs actual pitches for each model
- Rolling accuracy line chart showing model performance progression over the game

**UI Theme**: Vibrant "Backyard Baseball" aesthetic with:
- Comic Sans font for playful feel
- Bright, saturated colors (greens, yellows, oranges, blues)
- Bold borders and 3D shadow effects
- High-contrast charts with thick lines (4px) for readability

### Data Flow

1. Frontend fetches player list from `/api/players/list`
2. Both player and game date dropdowns are visible (game dropdown disabled until player selected)
3. User selects pitcher → Frontend calls `/api/players/stats`
4. Backend uses `playerid_lookup()` to get Statcast player ID
5. Backend fetches season data via `statcast_pitcher()` (cached in Redis, 24hr TTL)
6. User selects game date → Frontend calls `/api/predictions/game`
7. Backend fetches single-game data and maps pitch types via `data/pitch_map.json`
8. Backend extracts team info (`home_team`, `away_team`) from DataFrame
9. Backend determines pitcher's team using `inning_topbot` field:
   - `"Top"` = away team batting → home team pitching
   - `"Bot"` = home team batting → away team pitching
10. Backend runs all models in `AVAILABLE_MODELS` and collects performance metrics
11. Frontend renders interactive charts comparing model accuracies and predictions

### 3-Tier Caching Strategy

The application uses a 3-tier data caching strategy to minimize API calls and improve performance:

1. **PostgreSQL (Tier 1 - Permanent Storage)**
   - All Statcast data is permanently stored in Postgres
   - Tables: `statcast_pitches` (pitch-by-pitch data), `pitcher_game_cache` (tracking)
   - Checked first for every request
   - Models: `app/models/database.py`

2. **Redis (Tier 2 - Hot Cache)**
   - Recently accessed games cached for 1 hour
   - Fast in-memory lookups for repeated queries
   - Checked if data not found in Postgres
   - Data is saved to Postgres when loaded from Redis

3. **Statcast API (Tier 3 - Source of Truth)**
   - Fetched only if data not in Postgres or Redis
   - Automatically saved to both Postgres and Redis after fetching
   - Rate-limited by MLB, so minimizing calls is important

**Data Flow:** `fetch_game_stats()` checks Postgres → Redis → API and saves back down the chain.

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (defaults to `postgresql://localhost/aaronson_oracle_baseball`)
- `REDIS_URL`: Redis connection string (defaults to `redis://localhost:6379`)
- `PORT`: Backend server port (defaults to 8000)

### Constants

Key parameters in `backend/app/services/predictors.py`:
- `DEFAULT_PITCH_VALUE = "fast"`: Fallback prediction
- `PITCH_GRAM_SIZE = 3`: Default n-gram window size

## Deployment

### Single-Service Deployment (Railway)

The application is configured for a single-service deployment where FastAPI serves both the API and the React frontend:

**Dockerfile Build Process:**
1. Installs Node.js 18 in Python 3.11 base image
2. Builds React frontend (`npm run build` → creates `frontend/dist`)
3. Installs Python dependencies from `pyproject.toml`
4. Copies all application code

**FastAPI Static File Serving:**
- Frontend static assets mounted at `/assets`
- SPA catch-all route serves `index.html` for all non-API routes
- API endpoints remain at `/api/*`

**Environment-Aware API URLs:**
- Production: Frontend uses relative URLs (`/api`)
- Development: Frontend uses `http://localhost:8000/api`

**Required Environment Variables:**
- `PORT`: Server port (Railway provides this automatically)
- `REDIS_URL`: Redis connection string (defaults to `redis://localhost:6379`)

When deployed to Railway, the single service provides:
- **Frontend**: `https://your-app.railway.app/` (React UI)
- **API**: `https://your-app.railway.app/api/*` (FastAPI endpoints)
- **API Docs**: `https://your-app.railway.app/docs` (Swagger UI)
