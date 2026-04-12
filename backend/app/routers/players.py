"""Player-related API endpoints"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from sqlalchemy import distinct

from app.database import get_db
from app.models.database import PitcherGameCache, StatcastPitch
from app.models.schemas import PlayerRequest, PlayerStatsResponse
from app.services.baseball import get_player_id, fetch_and_cache_player_stats, get_pitcher_games_from_db


router = APIRouter()

DEFAULT_SEASON = 2025
START_DT = "2025-03-01"
END_DT = "2025-11-01"

PITCHERS_JSON = Path(__file__).parent.parent.parent.parent / "training" / "pitchers.json"


@router.post("/players/stats", response_model=PlayerStatsResponse)
async def get_player_stats(player_request: PlayerRequest, request: Request):
    """Get all game dates for a player — checks Postgres first, falls back to API"""
    try:
        player_id = get_player_id(player_request.player_name)

        # Try Postgres first (fast, no API call) — filter to current analysis season
        with get_db() as db:
            game_dates = get_pitcher_games_from_db(db, player_id, season=DEFAULT_SEASON)

        if game_dates:
            return PlayerStatsResponse(
                player_name=player_request.player_name,
                player_id=player_id,
                game_dates=game_dates,
            )

        # Fall back to Statcast API
        player_df = fetch_and_cache_player_stats(
            redis_client=request.app.state.redis,
            player_id=player_id,
            start_dt=START_DT,
            end_dt=END_DT,
        )

        game_dates = sorted(player_df["game_date"].unique().tolist())

        return PlayerStatsResponse(
            player_name=player_request.player_name,
            player_id=player_id,
            game_dates=game_dates,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching player stats: {str(e)}")


@router.get("/players/list")
async def get_players_list():
    """Get list of pitchers that have games in the default season."""
    try:
        with get_db() as db:
            rows = db.query(
                StatcastPitch.player_name
            ).filter(
                StatcastPitch.game_date >= f"{DEFAULT_SEASON}-01-01",
                StatcastPitch.game_date < f"{DEFAULT_SEASON + 1}-01-01",
            ).distinct().all()

            if rows:
                # DB names are "Last, First" — convert to "First Last"
                names = []
                for (name,) in rows:
                    parts = name.split(", ", 1)
                    if len(parts) == 2:
                        names.append(f"{parts[1]} {parts[0]}")
                    else:
                        names.append(name)
                return {"players": sorted(names)}
    except Exception:
        pass

    # Fallback to pitchers.json if DB is unavailable
    try:
        with open(PITCHERS_JSON) as f:
            data = json.load(f)
        return {"players": [p["name"] for p in data["pitchers"]]}
    except FileNotFoundError:
        return {"players": []}
