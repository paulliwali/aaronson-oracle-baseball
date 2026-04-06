"""Live game API endpoints"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from app.services.mlb_live import get_todays_games, get_live_pitches
from app.services.predictors import AVAILABLE_MODELS
from app.models.schemas import GamePredictionResponse, ModelPerformance


router = APIRouter()


@router.get("/live/games")
async def list_live_games():
    """Get today's MLB games with status and starting pitchers."""
    try:
        games = get_todays_games()
        return {"games": games, "count": len(games)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching live games: {str(e)}")


@router.get("/live/game/{game_pk}")
async def get_live_game(game_pk: int, pitcher: Optional[str] = None):
    """Get live pitch data + model predictions for a specific game.

    Optional query param `pitcher` filters to a specific pitcher's pitches.
    Response format matches GamePredictionResponse for frontend reuse.
    """
    try:
        df = get_live_pitches(game_pk, pitcher_name=pitcher)

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No pitch data found for game {game_pk}"
                + (f" (pitcher: {pitcher})" if pitcher else ""),
            )

        # Extract game info
        home_team = str(df["home_team"].iloc[0])
        away_team = str(df["away_team"].iloc[0])
        pitcher_name = str(df["player_name"].iloc[0])

        inning_topbot = str(df["inning_topbot"].iloc[0])
        pitcher_team = home_team if inning_topbot == "Top" else away_team

        pitch_distribution = df["pitch_type_simplified"].value_counts().to_dict()
        actual_pitches = df["pitch_type_simplified"].tolist()

        # Run all models
        models_performance = []
        actuals = df["pitch_type_simplified"]

        for model in AVAILABLE_MODELS:
            predictions = model.predict(df)
            accuracy = model.calculate_accuracy(predictions, actuals)
            rolling_accuracy = model.calculate_rolling_accuracy(predictions, actuals)

            models_performance.append(
                ModelPerformance(
                    model_name=model.name,
                    accuracy=accuracy,
                    rolling_accuracy=rolling_accuracy,
                    predictions=predictions,
                )
            )

        return GamePredictionResponse(
            player_name=pitcher_name,
            game_date=str(df["game_date"].iloc[0]),
            home_team=home_team,
            away_team=away_team,
            pitcher_team=pitcher_team,
            total_pitches=len(df),
            pitch_types_distribution=pitch_distribution,
            actual_pitches=actual_pitches,
            models=models_performance,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching live game data: {str(e)}")
