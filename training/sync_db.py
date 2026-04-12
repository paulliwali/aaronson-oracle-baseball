"""Bulk-sync Statcast pitcher data into Postgres.

Reads pitchers.json, fetches full seasons from Statcast API, and writes
each game into the StatcastPitch + PitcherGameCache tables. Tracks which
pitcher+season combos are fully synced via the PitcherSeason table so
subsequent runs skip already-synced data.

Requires DATABASE_URL env var (defaults to postgresql://localhost/aaronson_oracle_baseball).

Usage:
    uv run python training/sync_db.py
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
from pybaseball import statcast_pitcher

# Add backend/ to path so we can import app.database, app.models, etc.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import get_db, init_db
from app.models.database import PitcherGameCache, PitcherSeason, StatcastPitch

PITCHERS_PATH = Path(__file__).parent / "pitchers.json"
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"
API_DELAY_SECONDS = 5
MIN_PITCHES_PER_GAME = 60


def load_pitchers():
    with open(PITCHERS_PATH) as f:
        data = json.load(f)
    return data["pitchers"], data["seasons"]


def load_pitch_map():
    with open(PITCH_MAP_PATH) as f:
        return json.load(f)


def get_player_id(first: str, last: str) -> int:
    from pybaseball import playerid_lookup
    df = playerid_lookup(last=last, first=first)
    if df.empty:
        raise ValueError(f"Player not found: {first} {last}")
    return int(df["key_mlbam"].iloc[0])


def is_season_synced(db, pitcher_id: int, season: int) -> bool:
    return db.query(PitcherSeason).filter(
        PitcherSeason.pitcher_id == pitcher_id,
        PitcherSeason.season == season,
    ).first() is not None


def _safe_float(val):
    """Convert a value to float, returning None if not numeric."""
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val, default=0):
    """Convert a value to int, returning default if not numeric."""
    if pd.isna(val):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def save_game_to_postgres(db, game_df: pd.DataFrame, player_id: int, game_date: str):
    """Save a single game's pitches to Postgres. Skip if already cached."""
    existing = db.query(PitcherGameCache).filter(
        PitcherGameCache.pitcher_id == player_id,
        PitcherGameCache.game_date == game_date,
    ).first()
    if existing:
        return False  # already cached

    game_pk = _safe_int(game_df["game_pk"].iloc[0]) if "game_pk" in game_df.columns else 0

    # Check for any existing pitches for this game (partial prior sync)
    existing_count = db.query(StatcastPitch).filter(
        StatcastPitch.game_pk == game_pk,
        StatcastPitch.pitcher == player_id,
    ).count()
    if existing_count > 0:
        # Already have pitches but no cache record — just add the cache record
        cache_record = PitcherGameCache(
            pitcher_id=player_id,
            game_date=game_date,
            game_pk=game_pk,
            total_pitches=existing_count,
        )
        db.add(cache_record)
        return True

    for _, row in game_df.iterrows():
        pitch = StatcastPitch(
            game_pk=_safe_int(row.get("game_pk", game_pk)),
            game_date=game_date,
            pitcher=player_id,
            player_name=str(row.get("player_name", "")),
            batter=_safe_int(row.get("batter", 0)),
            home_team=str(row.get("home_team", "")),
            away_team=str(row.get("away_team", "")),
            inning_topbot=str(row.get("inning_topbot", "")),
            inning=_safe_int(row.get("inning", 0)),
            pitch_type=str(row.get("pitch_type")) if pd.notna(row.get("pitch_type")) else None,
            pitch_type_simplified=str(row.get("pitch_type_simplified")) if pd.notna(row.get("pitch_type_simplified")) else None,
            pitch_name=str(row.get("pitch_name")) if pd.notna(row.get("pitch_name")) else None,
            release_speed=_safe_float(row.get("release_speed")),
            release_spin_rate=_safe_int(row.get("release_spin_rate")) if pd.notna(row.get("release_spin_rate")) else None,
            plate_x=_safe_float(row.get("plate_x")),
            plate_z=_safe_float(row.get("plate_z")),
            balls=_safe_int(row.get("balls", 0)),
            strikes=_safe_int(row.get("strikes", 0)),
            outs_when_up=_safe_int(row.get("outs_when_up", 0)),
            pitch_number=_safe_int(row.get("pitch_number", 0)),
            at_bat_number=_safe_int(row.get("at_bat_number", 0)),
            events=str(row.get("events")) if pd.notna(row.get("events")) else None,
            description=str(row.get("description")) if pd.notna(row.get("description")) else None,
            type=str(row.get("type")) if pd.notna(row.get("type")) else None,
            home_score=_safe_int(row.get("home_score", 0)),
            away_score=_safe_int(row.get("away_score", 0)),
        )
        db.add(pitch)

    cache_record = PitcherGameCache(
        pitcher_id=player_id,
        game_date=game_date,
        game_pk=game_pk,
        total_pitches=len(game_df),
    )
    db.add(cache_record)
    return True


def sync_pitcher_season(db, pitcher: dict, season: int, pitch_map: dict) -> dict:
    """Sync one pitcher-season into Postgres. Returns stats dict."""
    try:
        player_id = pitcher.get("mlbam_id") or get_player_id(pitcher["first"], pitcher["last"])
    except ValueError as e:
        return {"status": "error", "error": str(e)}

    if is_season_synced(db, player_id, season):
        return {"status": "skipped", "reason": "already synced"}

    start_dt = f"{season}-03-01"
    end_dt = f"{season}-11-30"

    print(f"  Fetching {pitcher['name']} {season} (ID: {player_id})...")
    try:
        df = statcast_pitcher(start_dt=start_dt, end_dt=end_dt, player_id=player_id)
    except Exception as e:
        return {"status": "error", "error": f"API fetch failed: {e}"}

    if df.empty:
        return {"status": "empty", "reason": "no data from API"}

    df = df.copy()
    df["pitch_type_simplified"] = df["pitch_type"].map(pitch_map)
    df = df.dropna(subset=["pitch_type_simplified"])

    # Filter to starter appearances (>= MIN_PITCHES_PER_GAME pitches)
    game_pitch_counts = df.groupby("game_date").size()
    starter_dates = game_pitch_counts[game_pitch_counts >= MIN_PITCHES_PER_GAME].index
    df = df[df["game_date"].isin(starter_dates)]

    if df.empty:
        return {"status": "empty", "reason": "no starter appearances"}

    total_games = 0
    total_pitches = 0
    new_games = 0

    for game_date, game_df in df.groupby("game_date"):
        game_df = game_df.sort_values("pitch_number").reset_index(drop=True)
        was_new = save_game_to_postgres(db, game_df, player_id, str(game_date))
        total_games += 1
        total_pitches += len(game_df)
        if was_new:
            new_games += 1

    # Mark season as synced
    season_record = PitcherSeason(
        pitcher_id=player_id,
        pitcher_name=pitcher["name"],
        season=season,
        total_games=total_games,
        total_pitches=total_pitches,
    )
    db.add(season_record)
    db.flush()

    return {
        "status": "synced",
        "total_games": total_games,
        "new_games": new_games,
        "total_pitches": total_pitches,
    }


def main():
    init_db()
    pitchers, seasons = load_pitchers()
    pitch_map = load_pitch_map()

    total_pairs = len(pitchers) * len(seasons)
    synced = 0
    skipped = 0
    errors = 0
    done = 0

    print(f"Syncing {len(pitchers)} pitchers x {len(seasons)} seasons = {total_pairs} pairs")
    print()

    for pitcher in pitchers:
        print(f"{'=' * 50}")
        print(f"Pitcher: {pitcher['name']}")
        print(f"{'=' * 50}")

        for season in seasons:
            done += 1
            print(f"\n  [{done}/{total_pairs}] {pitcher['name']} {season}")

            with get_db() as db:
                result = sync_pitcher_season(db, pitcher, season, pitch_map)

            status = result["status"]
            if status == "synced":
                synced += 1
                print(f"  Synced: {result['total_games']} games, {result['total_pitches']} pitches ({result['new_games']} new)")
            elif status == "skipped":
                skipped += 1
                print(f"  Skipped: {result['reason']}")
            elif status == "empty":
                skipped += 1
                print(f"  Empty: {result['reason']}")
            else:
                errors += 1
                print(f"  ERROR: {result.get('error', 'unknown')}")

            # Rate limit between API calls
            if done < total_pairs and status not in ("skipped",):
                print(f"  Waiting {API_DELAY_SECONDS}s...")
                time.sleep(API_DELAY_SECONDS)

    print(f"\n{'=' * 50}")
    print(f"Done: {done}/{total_pairs}")
    print(f"  Synced: {synced}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
