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
    total_pitches: int
    pitch_types_distribution: Dict[str, int]
    actual_pitches: List[str]
    models: List[ModelPerformance]
