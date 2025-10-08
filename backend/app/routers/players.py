"""Player-related API endpoints"""

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import PlayerRequest, PlayerStatsResponse
from app.services.baseball import get_player_id, fetch_and_cache_player_stats


router = APIRouter()

START_DT = "2023-04-01"
END_DT = "2023-09-01"


@router.post("/players/stats", response_model=PlayerStatsResponse)
async def get_player_stats(player_request: PlayerRequest, request: Request):
    """Get all game dates for a player within the date range"""
    try:
        player_id = get_player_id(player_request.player_name)

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
    """Get hardcoded list of popular pitchers"""
    return {
        "players": [
            "Logan Webb",
            "Corbin Burnes",
            "Zac Gallen",
            "Gerrit Cole",
            "Blake Snell",
            "Zack Wheeler",
            "Kodai Senga",
        ]
    }
