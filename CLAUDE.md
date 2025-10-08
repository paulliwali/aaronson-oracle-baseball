# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack web application that adapts [Aaronson's Oracle](https://github.com/elsehow/aaronson-oracle/blob/master/README.md) algorithm to predict baseball pitches. It compares multiple prediction models to determine which algorithm best anticipates a pitcher's next pitch type.

The application uses:
- **Backend**: FastAPI (Python) for REST API
- **Frontend**: React + Vite for visualization
- **Data**: PyBaseball (Statcast API) for MLB pitch data
- **Caching**: Redis for API response caching

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
python run.py
```
The API will be available at http://localhost:8000 with interactive docs at http://localhost:8000/docs

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
- Returns: Performance metrics for all models on that specific game

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
- Game metadata (pitcher, date, total pitches)
- Pitch type distribution
- Final accuracy table for all models
- Rolling accuracy line chart showing model performance over the course of the game

### Data Flow

1. Frontend fetches player list from `/api/players/list`
2. User selects pitcher → Frontend calls `/api/players/stats`
3. Backend uses `playerid_lookup()` to get Statcast player ID
4. Backend fetches season data via `statcast_pitcher()` (cached in Redis, 24hr TTL)
5. User selects game date → Frontend calls `/api/predictions/game`
6. Backend fetches single-game data and maps pitch types via `data/pitch_map.json`
7. Backend runs all models in `AVAILABLE_MODELS` and collects performance metrics
8. Frontend renders interactive chart comparing model accuracies

### Environment Variables

- `REDIS_URL`: Redis connection string (defaults to `redis://localhost:6379`)
- `PORT`: Backend server port (defaults to 8000)

### Constants

Key parameters in `backend/app/services/predictors.py`:
- `DEFAULT_PITCH_VALUE = "fast"`: Fallback prediction
- `PITCH_GRAM_SIZE = 3`: Default n-gram window size
