"""Baseball data fetching and caching service with 3-tier caching: Postgres -> Redis -> API"""

import json
import os
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
import redis
from pybaseball import playerid_lookup, statcast_pitcher
from sqlalchemy.orm import Session

from app.models.database import StatcastPitch, PitcherGameCache
from app.database import get_db


REDIS_CACHE_FORMAT = "game:{player_id}:{game_date}"
REDIS_CACHE_TTL = 3600  # 1 hour for Redis (shorter since Postgres is primary)


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


def get_pitcher_games_from_db(db: Session, player_id: int, season: Optional[int] = None) -> Optional[list]:
    """Get cached game dates for a pitcher from Postgres.

    If season is provided, filters to that year only.
    Returns sorted list of game_date strings, or None if no data found.
    """
    query = db.query(PitcherGameCache.game_date).filter(
        PitcherGameCache.pitcher_id == player_id,
    )

    if season:
        query = query.filter(
            PitcherGameCache.game_date >= f"{season}-01-01",
            PitcherGameCache.game_date < f"{season + 1}-01-01",
        )

    records = query.order_by(PitcherGameCache.game_date).all()

    if not records:
        return None

    return [r.game_date for r in records]


def _load_from_postgres(db: Session, player_id: int, game_date: str) -> Optional[pd.DataFrame]:
    """Load game data from Postgres database"""
    pitches = db.query(StatcastPitch).filter(
        StatcastPitch.pitcher == player_id,
        StatcastPitch.game_date == game_date
    ).order_by(StatcastPitch.at_bat_number, StatcastPitch.pitch_number).all()

    if not pitches:
        return None

    # Convert SQLAlchemy objects to DataFrame
    data = []
    for pitch in pitches:
        data.append({
            'game_pk': pitch.game_pk,
            'game_date': pitch.game_date,
            'pitcher': pitch.pitcher,
            'player_name': pitch.player_name,
            'batter': pitch.batter,
            'home_team': pitch.home_team,
            'away_team': pitch.away_team,
            'inning_topbot': pitch.inning_topbot,
            'inning': pitch.inning,
            'pitch_type': pitch.pitch_type,
            'pitch_type_simplified': pitch.pitch_type_simplified,
            'pitch_name': pitch.pitch_name,
            'release_speed': pitch.release_speed,
            'release_spin_rate': pitch.release_spin_rate,
            'plate_x': pitch.plate_x,
            'plate_z': pitch.plate_z,
            'balls': pitch.balls,
            'strikes': pitch.strikes,
            'outs_when_up': pitch.outs_when_up,
            'pitch_number': pitch.pitch_number,
            'at_bat_number': pitch.at_bat_number,
            'events': pitch.events,
            'description': pitch.description,
            'type': pitch.type,
            'home_score': pitch.home_score,
            'away_score': pitch.away_score,
        })

    return pd.DataFrame(data)


def _safe_float(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val, default=0):
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _save_to_postgres(db: Session, game_stats_df: pd.DataFrame, player_id: int, game_date: str):
    """Save game data to Postgres database"""
    try:
        if game_stats_df.empty:
            return

        # Check if already cached
        existing = db.query(PitcherGameCache).filter(
            PitcherGameCache.pitcher_id == player_id,
            PitcherGameCache.game_date == game_date
        ).first()

        if existing:
            return  # Already cached

        # Get game_pk from the data
        game_pk = _safe_int(game_stats_df['game_pk'].iloc[0]) if 'game_pk' in game_stats_df.columns else 0

        # Insert all pitches
        for _, row in game_stats_df.iterrows():
            pitch = StatcastPitch(
                game_pk=_safe_int(row.get('game_pk', game_pk)),
                game_date=game_date,
                pitcher=player_id,
                player_name=str(row.get('player_name', '')),
                batter=_safe_int(row.get('batter', 0)),
                home_team=str(row.get('home_team', '')),
                away_team=str(row.get('away_team', '')),
                inning_topbot=str(row.get('inning_topbot', '')),
                inning=_safe_int(row.get('inning', 0)),
                pitch_type=str(row.get('pitch_type')) if pd.notna(row.get('pitch_type')) else None,
                pitch_type_simplified=str(row.get('pitch_type_simplified')) if pd.notna(row.get('pitch_type_simplified')) else None,
                pitch_name=str(row.get('pitch_name')) if pd.notna(row.get('pitch_name')) else None,
                release_speed=_safe_float(row.get('release_speed')),
                release_spin_rate=_safe_int(row.get('release_spin_rate')) if pd.notna(row.get('release_spin_rate')) else None,
                plate_x=_safe_float(row.get('plate_x')),
                plate_z=_safe_float(row.get('plate_z')),
                balls=_safe_int(row.get('balls', 0)),
                strikes=_safe_int(row.get('strikes', 0)),
                outs_when_up=_safe_int(row.get('outs_when_up', 0)),
                pitch_number=_safe_int(row.get('pitch_number', 0)),
                at_bat_number=_safe_int(row.get('at_bat_number', 0)),
                events=str(row.get('events')) if pd.notna(row.get('events')) else None,
                description=str(row.get('description')) if pd.notna(row.get('description')) else None,
                type=str(row.get('type')) if pd.notna(row.get('type')) else None,
                home_score=_safe_int(row.get('home_score', 0)),
                away_score=_safe_int(row.get('away_score', 0)),
            )
            db.add(pitch)

        # Add cache record
        cache_record = PitcherGameCache(
            pitcher_id=player_id,
            game_date=game_date,
            game_pk=game_pk,
            total_pitches=len(game_stats_df)
        )
        db.add(cache_record)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving to Postgres: {e}")


def fetch_and_cache_player_stats(
    redis_client: redis.Redis,
    player_id: int,
    start_dt: str,
    end_dt: str,
) -> pd.DataFrame:
    """Fetch and cache the player stats for a date range (used for getting game list)"""
    cache_key = f"season:{player_id}:{start_dt}:{end_dt}"

    # Check Redis first
    cache_data = redis_client.get(cache_key)
    if cache_data:
        return pd.read_json(StringIO(cache_data))

    # Fetch from API
    selected_player_df = statcast_pitcher(
        player_id=player_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    # Cache in Redis (shorter TTL for season data)
    redis_client.set(cache_key, selected_player_df.to_json(orient="records"), ex=86400)
    return selected_player_df


def fetch_game_stats(
    player_id: int,
    game_date: str,
    redis_client: Optional[redis.Redis] = None,
) -> pd.DataFrame:
    """
    Fetch stats for a specific game using 3-tier caching:
    1. Check Postgres (permanent storage)
    2. Check Redis (recent queries)
    3. Fetch from Statcast API and store in both
    """
    # Tier 1: Check Postgres
    with get_db() as db:
        df_from_postgres = _load_from_postgres(db, player_id, game_date)
        if df_from_postgres is not None and not df_from_postgres.empty:
            print(f"✓ Loaded from Postgres: {player_id} on {game_date}")
            return df_from_postgres

    # Tier 2: Check Redis (if available)
    if redis_client:
        cache_key = REDIS_CACHE_FORMAT.format(player_id=player_id, game_date=game_date)
        cache_data = redis_client.get(cache_key)
        if cache_data:
            print(f"✓ Loaded from Redis: {player_id} on {game_date}")
            df_from_redis = pd.read_json(StringIO(cache_data))
            # Save to Postgres for permanent storage
            with get_db() as db:
                _save_to_postgres(db, df_from_redis, player_id, game_date)
            return df_from_redis

    # Tier 3: Fetch from Statcast API
    print(f"⬇ Fetching from API: {player_id} on {game_date}")
    game_stats_df = statcast_pitcher(
        start_dt=game_date,
        end_dt=game_date,
        player_id=player_id,
    )

    # Apply pitch type mapping
    game_stats_df = map_pitch_type(game_stats_df)

    # Save to Postgres
    with get_db() as db:
        _save_to_postgres(db, game_stats_df, player_id, game_date)

    # Save to Redis
    if redis_client:
        cache_key = REDIS_CACHE_FORMAT.format(player_id=player_id, game_date=game_date)
        redis_client.set(cache_key, game_stats_df.to_json(orient="records"), ex=REDIS_CACHE_TTL)

    return game_stats_df
