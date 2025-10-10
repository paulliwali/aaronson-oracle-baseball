"""Baseball data fetching and caching service"""

import json
import os
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
import redis
from pybaseball import playerid_lookup, statcast_pitcher


CACHE_FILE_FORMAT = "{player_id}_{start_dt}_{end_dt}"
CACHE_TTL = 86400  # 24 hours


def get_player_id(player_name: str) -> int:
    """Get the Statcast player ID given the player name"""
    parts = player_name.split(" ")
    if len(parts) < 2:
        raise ValueError("Player name must include first and last name")

    first_name = parts[0]
    last_name = " ".join(parts[1:])

    playerid_lookup_df = playerid_lookup(last=last_name, first=first_name)

    if playerid_lookup_df.empty:
        raise ValueError(f"Player not found: {player_name}")

    return int(playerid_lookup_df["key_mlbam"].iloc[0])


def map_pitch_type(game_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Map the Statcast pitch type to a simplified version"""
    # Get the project root directory (two levels up from this file)
    project_root = Path(__file__).parent.parent.parent.parent
    pitch_map_path = project_root / "data" / "pitch_map.json"

    with open(pitch_map_path, "r") as f:
        pitch_map = json.load(f)

    game_stats_df["pitch_type_simplified"] = game_stats_df["pitch_type"].replace(pitch_map)
    return game_stats_df


def fetch_and_cache_player_stats(
    redis_client: redis.Redis,
    player_id: int,
    start_dt: str,
    end_dt: str,
) -> pd.DataFrame:
    """Fetch and cache the player stats, read from cache if available"""
    cache_key = CACHE_FILE_FORMAT.format(
        player_id=player_id, start_dt=start_dt, end_dt=end_dt
    )

    cache_data = redis_client.get(cache_key)
    if cache_data:
        return pd.read_json(StringIO(cache_data))

    selected_player_df = statcast_pitcher(
        player_id=player_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    redis_client.set(cache_key, selected_player_df.to_json(orient="records"), ex=CACHE_TTL)
    return selected_player_df


def fetch_game_stats(
    player_id: int,
    game_date: str,
) -> pd.DataFrame:
    """Fetch stats for a specific game"""
    game_stats_df = statcast_pitcher(
        start_dt=game_date,
        end_dt=game_date,
        player_id=player_id,
    )

    return map_pitch_type(game_stats_df)
