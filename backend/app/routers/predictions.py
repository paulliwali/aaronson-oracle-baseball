"""Prediction-related API endpoints"""

from functools import lru_cache

import statsapi
from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    GameContext,
    GamePredictionRequest,
    GamePredictionResponse,
    ModelPerformance,
    PitchPredictionRequest,
    PitchPredictionResponse,
)
from app.services.baseball import get_player_id, fetch_game_stats
from app.services.predictors import AVAILABLE_MODELS


@lru_cache(maxsize=1024)
def _batter_name(batter_id: int) -> str:
    """Resolve MLBAM batter ID to full name. Cached across requests."""
    try:
        data = statsapi.get("person", {"personId": batter_id})
        people = data.get("people", [])
        if people:
            return people[0].get("fullName", "")
    except Exception:
        pass
    return ""


router = APIRouter()


@router.post("/predictions/game", response_model=GamePredictionResponse)
async def get_game_predictions(prediction_request: GamePredictionRequest, request: Request):
    """Get predictions for a specific game using all available models"""
    try:
        player_id = get_player_id(prediction_request.player_name)

        # Get Redis client from app state
        redis_client = request.app.state.redis if hasattr(request.app.state, 'redis') else None

        # Fetch game stats (will check Postgres -> Redis -> API)
        game_stats_df = fetch_game_stats(
            player_id=player_id,
            game_date=prediction_request.game_date,
            redis_client=redis_client,
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


@router.post("/predictions/pitch", response_model=PitchPredictionResponse)
async def get_pitch_prediction(req: PitchPredictionRequest, request: Request):
    """Get model predictions for a single pitch in playback mode.

    Returns the game context at pitch_index, model predictions for that pitch,
    and all previously revealed pitches.
    """
    try:
        player_id = get_player_id(req.player_name)
        redis_client = request.app.state.redis if hasattr(request.app.state, "redis") else None

        game_stats_df = fetch_game_stats(
            player_id=player_id,
            game_date=req.game_date,
            redis_client=redis_client,
        )

        if game_stats_df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {req.player_name} on {req.game_date}",
            )

        total_pitches = len(game_stats_df)

        if req.pitch_index >= total_pitches:
            raise HTTPException(
                status_code=400,
                detail=f"pitch_index {req.pitch_index} out of range (game has {total_pitches} pitches)",
            )

        # Slice the game up to and including the current pitch
        # Models need the full slice to make sequential predictions
        slice_df = game_stats_df.iloc[: req.pitch_index + 1].copy()

        # Build game context for the current pitch
        current_row = game_stats_df.iloc[req.pitch_index]
        home_team = str(current_row.get("home_team", ""))
        away_team = str(current_row.get("away_team", ""))
        inning_topbot = str(current_row.get("inning_topbot", "Top"))
        pitcher_team = home_team if inning_topbot == "Top" else away_team

        # Resolve batter name
        batter_id = int(current_row.get("batter", 0))
        batter_name = _batter_name(batter_id) if batter_id else ""

        context = GameContext(
            balls=int(current_row.get("balls", 0)),
            strikes=int(current_row.get("strikes", 0)),
            outs=int(current_row.get("outs_when_up", 0)),
            inning=int(current_row.get("inning", 1)),
            inning_half=inning_topbot,
            home_score=int(current_row.get("home_score", 0)),
            away_score=int(current_row.get("away_score", 0)),
            home_team=home_team,
            away_team=away_team,
            pitcher_team=pitcher_team,
            batter_name=batter_name,
            at_bat_number=int(current_row.get("at_bat_number", 0)),
        )

        # Run each model on the slice, take the last prediction
        model_predictions = {}
        for model in AVAILABLE_MODELS:
            preds = model.predict(slice_df)
            model_predictions[model.name] = preds[-1] if preds else "fast"

        # Previously revealed pitches (everything before pitch_index)
        revealed = game_stats_df["pitch_type_simplified"].iloc[: req.pitch_index].tolist()
        revealed_abs = game_stats_df["at_bat_number"].iloc[: req.pitch_index].astype(int).tolist()

        # Actual pitch at the current index
        actual = str(game_stats_df["pitch_type_simplified"].iloc[req.pitch_index])

        return PitchPredictionResponse(
            revealed_pitches=revealed,
            revealed_at_bats=revealed_abs,
            model_predictions=model_predictions,
            actual_pitch=actual,
            total_pitches=total_pitches,
            game_context=context,
            is_last_pitch=(req.pitch_index == total_pitches - 1),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating pitch prediction: {str(e)}")
