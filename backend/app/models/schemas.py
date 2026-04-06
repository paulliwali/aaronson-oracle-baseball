"""Pydantic schemas for API request/response validation"""

from typing import List, Dict
from pydantic import BaseModel, Field


class PlayerRequest(BaseModel):
    """Request to get player stats"""
    player_name: str = Field(..., description="Full name of the player (e.g., 'Logan Webb')")


class PlayerStatsResponse(BaseModel):
    """Response containing player game dates"""
    player_name: str
    player_id: int
    game_dates: List[str]


class GamePredictionRequest(BaseModel):
    """Request to get game predictions"""
    player_name: str
    game_date: str = Field(..., description="Game date in YYYY-MM-DD format")


class ModelPerformance(BaseModel):
    """Performance metrics for a prediction model"""
    model_name: str
    accuracy: float
    rolling_accuracy: List[float]
    predictions: List[str]


class GamePredictionResponse(BaseModel):
    """Response containing game predictions and model performance"""
    player_name: str
    game_date: str
    home_team: str
    away_team: str
    pitcher_team: str
    total_pitches: int
    pitch_types_distribution: Dict[str, int]
    actual_pitches: List[str]
    models: List[ModelPerformance]


# --- Playback mode schemas ---

class GameContext(BaseModel):
    """Current game situation for the pitch about to be thrown"""
    balls: int
    strikes: int
    outs: int
    inning: int
    inning_half: str  # "Top" or "Bot"
    home_score: int
    away_score: int
    home_team: str = ""
    away_team: str = ""
    pitcher_team: str = ""
    batter_name: str = ""
    at_bat_number: int = 0

class PitchPredictionRequest(BaseModel):
    """Request for a single pitch prediction in playback mode"""
    player_name: str
    game_date: str = Field(..., description="Game date in YYYY-MM-DD format")
    pitch_index: int = Field(..., ge=0, description="0-based index of the pitch to predict")

class PitchPredictionResponse(BaseModel):
    """Response for a single pitch in playback mode"""
    revealed_pitches: List[str]
    revealed_at_bats: List[int]
    model_predictions: Dict[str, str]
    actual_pitch: str
    total_pitches: int
    game_context: GameContext
    is_last_pitch: bool
