# Aaronson Oracle Baseball

A full-stack web application that adapts [Aaronson's Oracle](https://github.com/elsehow/aaronson-oracle/blob/master/README.md) algorithm to predict baseball pitches. Compare multiple prediction models to determine which algorithm best anticipates a pitcher's next pitch type.

![Baseball Pitch Prediction](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![React](https://img.shields.io/badge/React-18+-61dafb.svg)

## Overview

The application uses n-gram pattern matching and other algorithms to predict a starting pitcher's next pitch based on their recent pitch history. Pitch predictions are visualized alongside rolling accuracy metrics to show how each model performs throughout a game.

### Key Features

- 📊 **Interactive Visualizations**: Scatter plots showing actual vs predicted pitches, aligned with rolling accuracy charts
- 🎯 **Multiple Prediction Models**: Compare naive baseline, n-gram (n=3,4), and frequency-based predictors
- ⚡ **Real-time Analysis**: Analyze any MLB pitcher's game from the 2023 season
- ⚾ **Team Matchup Info**: See home/away teams and which team the pitcher plays for
- 🎮 **Backyard Baseball Theme**: Fun, vibrant UI inspired by the classic video game with bold colors and playful design

### Tech Stack

- **Backend**: FastAPI (Python) with Pydantic validation
- **Frontend**: React + Vite with Recharts for visualizations
- **Data**: PyBaseball (Statcast API) for MLB pitch-by-pitch data
- **Caching**: Redis for optimized API response times

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 16+
- Redis server

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/aaronson-oracle-baseball.git
   cd aaronson-oracle-baseball
   ```

2. **Install Python dependencies**
   ```bash
   pip install -e .
   # Or with dev dependencies
   pip install -e ".[dev]"
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Start Redis** (if not already running)
   ```bash
   redis-server
   # Or on macOS with Homebrew
   brew services start redis
   ```

### Running the Application

**Terminal 1 - Backend:**
```bash
cd backend
python3 run.py  # Use python3 on macOS/Linux
```
API available at http://localhost:8000
Interactive docs at http://localhost:8000/docs

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
Web app available at http://localhost:5173

## How It Works

### Pitch Type Simplification

Statcast tracks 13+ different pitch types. For simplicity, we consolidate them into three categories:

- **Fast**: FF (four-seam), SI (sinker), FC (cutter), FS (splitter), FO (forkball)
- **Breaking**: CU (curveball), SL (slider), KC (knuckle curve), SV (slurve), SC (screwball), ST (sweeper), EP (eephus)
- **Off-Speed**: CH (changeup), KN (knuckleball)

### Team Detection

The app automatically determines which team the pitcher plays for by analyzing the `inning_topbot` field in Statcast data:
- **Top of inning**: Away team batting → Home team pitching
- **Bottom of inning**: Home team batting → Away team pitching

This allows the UI to display the full matchup context (e.g., "Logan Webb (SF) - SD @ SF").

### Prediction Algorithm (N-Gram)

1. Fetch pitch-by-pitch data from Statcast using `pybaseball`
2. Initialize a dictionary storing n-gram sequences as keys
3. For each pitch, look at the previous n pitches to form a pattern
4. Predict the most common pitch type that follows this pattern
5. Update the model with the actual pitch thrown
6. Default to "fast" if no historical pattern exists

## Project Structure

```
aaronson-oracle-baseball/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app setup
│   │   ├── models/schemas.py     # Pydantic models
│   │   ├── routers/              # API endpoints
│   │   │   ├── players.py
│   │   │   └── predictions.py
│   │   └── services/             # Business logic
│   │       ├── baseball.py       # Data fetching & caching
│   │       └── predictors.py     # Prediction models
│   └── run.py                    # Server entry point
├── frontend/
│   └── src/
│       ├── App.jsx               # Main application
│       └── components/
│           ├── PlayerSelector.jsx
│           ├── GameSelector.jsx
│           └── ModelComparison.jsx  # Charts & viz
├── data/
│   └── pitch_map.json            # Pitch type mappings
└── pyproject.toml                # Python dependencies
```

## API Endpoints

### `GET /api/players/list`
Returns list of available pitchers

### `POST /api/players/stats`
**Request:**
```json
{
  "player_name": "Logan Webb"
}
```
**Response:** Player ID and available game dates

### `POST /api/predictions/game`
**Request:**
```json
{
  "player_name": "Logan Webb",
  "game_date": "2023-05-15"
}
```
**Response:** Model predictions, accuracies, pitch sequences, and game context including:
- Home/away team matchup
- Pitcher's team affiliation (auto-detected from game data)
- Pitch type distribution
- Per-model performance metrics

## Adding New Prediction Models

1. Create a class extending `BasePredictorModel` in `backend/app/services/predictors.py`
2. Implement the `predict(game_stats_df)` method
3. Add an instance to the `AVAILABLE_MODELS` list

Example:
```python
class MyCustomPredictor(BasePredictorModel):
    def __init__(self):
        super().__init__("My Model Name")

    def predict(self, game_stats_df: pd.DataFrame) -> List[str]:
        # Your prediction logic here
        return predictions

# Add to registry
AVAILABLE_MODELS.append(MyCustomPredictor())
```

## Environment Variables

- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379`)
- `PORT`: Backend server port (default: `8000`, Railway sets this automatically)

## Deployment

The application is deployed as a single service where FastAPI serves both the API and React frontend.

### Railway Deployment

The Dockerfile is configured to:
1. Install Node.js and build the React frontend
2. Install Python dependencies
3. Serve frontend static files from FastAPI

**Deployment URLs:**
- Frontend: `https://your-app.railway.app/`
- API: `https://your-app.railway.app/api/*`
- API Docs: `https://your-app.railway.app/docs`

The frontend automatically uses relative URLs (`/api`) in production, so no environment variables needed for the frontend.

### Manual Deployment

To deploy elsewhere:
```bash
# Build frontend
cd frontend && npm run build

# Run with Docker
docker build -t aaronson-oracle-baseball .
docker run -p 8000:8000 -e REDIS_URL=your-redis-url aaronson-oracle-baseball
```

## Development

### Build frontend for production
```bash
cd frontend
npm run build
```

### Run tests (if available)
```bash
pip install -e ".[dev]"
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Aaronson's Oracle](https://github.com/elsehow/aaronson-oracle) - Original n-gram prediction concept
- [PyBaseball](https://github.com/jldbc/pybaseball) - Statcast data access
- MLB Statcast - Pitch tracking data
