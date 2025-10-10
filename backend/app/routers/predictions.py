"""Prediction-related API endpoints"""

from fastapi import APIRouter, HTTPException

from app.models.schemas import GamePredictionRequest, GamePredictionResponse, ModelPerformance
from app.services.baseball import get_player_id, fetch_game_stats
from app.services.predictors import AVAILABLE_MODELS


router = APIRouter()


@router.post("/predictions/game", response_model=GamePredictionResponse)
async def get_game_predictions(prediction_request: GamePredictionRequest):
    """Get predictions for a specific game using all available models"""
    try:
        player_id = get_player_id(prediction_request.player_name)

        # Fetch game stats
        game_stats_df = fetch_game_stats(
            player_id=player_id,
            game_date=prediction_request.game_date,
        )

        if game_stats_df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {prediction_request.player_name} on {prediction_request.game_date}",
            )

        # Extract team information from the game data
        home_team = game_stats_df["home_team"].iloc[0] if "home_team" in game_stats_df.columns else "N/A"
        away_team = game_stats_df["away_team"].iloc[0] if "away_team" in game_stats_df.columns else "N/A"

        # Determine which team the pitcher plays for based on inning_topbot
        # Top = away team batting, home team pitching
        # Bot = home team batting, away team pitching
        inning_topbot = game_stats_df["inning_topbot"].iloc[0] if "inning_topbot" in game_stats_df.columns else None
        pitcher_team = home_team if inning_topbot == "Top" else away_team if inning_topbot == "Bot" else "N/A"

        # Calculate pitch type distribution
        pitch_distribution = game_stats_df["pitch_type_simplified"].value_counts().to_dict()

        # Run all models and collect performance metrics
        models_performance = []
        actuals = game_stats_df["pitch_type_simplified"]
        actual_pitches_list = actuals.tolist()

        for model in AVAILABLE_MODELS:
            predictions = model.predict(game_stats_df)
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
            player_name=prediction_request.player_name,
            game_date=prediction_request.game_date,
            home_team=home_team,
            away_team=away_team,
            pitcher_team=pitcher_team,
            total_pitches=len(game_stats_df),
            pitch_types_distribution=pitch_distribution,
            actual_pitches=actual_pitches_list,
            models=models_performance,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")
