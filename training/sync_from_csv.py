"""Sync Postgres from already-downloaded CSV files (no API calls).

Reads all CSVs in data/training/, inserts pitches into Postgres,
and updates the pitcher_game_cache and pitcher_seasons tables.

Usage: DATABASE_URL="..." uv run python training/sync_from_csv.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import get_db, init_db
from app.models.database import PitcherGameCache, PitcherSeason, StatcastPitch

DATA_DIR = PROJECT_ROOT / "data" / "training"
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"


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


def main():
    init_db()

    with open(PITCH_MAP_PATH) as f:
        pitch_map = json.load(f)

    csv_files = sorted(DATA_DIR.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")

    # Group by pitcher+season from filename
    synced = 0
    skipped = 0
    errors = 0

    for i, csv_path in enumerate(csv_files):
        stem = csv_path.stem
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        try:
            season = int(parts[1])
        except ValueError:
            continue

        df = pd.read_csv(csv_path)
        if df.empty:
            continue

        pitcher_id = _safe_int(df["pitcher"].iloc[0])
        pitcher_name = str(df["player_name"].iloc[0]) if "player_name" in df.columns else stem

        # Check if already synced
        with get_db() as db:
            existing = db.query(PitcherSeason).filter(
                PitcherSeason.pitcher_id == pitcher_id,
                PitcherSeason.season == season,
            ).first()
            if existing:
                skipped += 1
                continue

        # Ensure pitch_type_simplified exists
        if "pitch_type_simplified" not in df.columns:
            df["pitch_type_simplified"] = df["pitch_type"].map(pitch_map)
            df = df.dropna(subset=["pitch_type_simplified"])

        if df.empty:
            continue

        print(f"  [{i+1}/{len(csv_files)}] {pitcher_name} {season}: {len(df)} pitches...", end=" ")

        try:
            with get_db() as db:
                total_games = 0
                for game_date, game_df in df.groupby("game_date"):
                    game_date_str = str(game_date)[:10]

                    # Skip if game already cached
                    existing_cache = db.query(PitcherGameCache).filter(
                        PitcherGameCache.pitcher_id == pitcher_id,
                        PitcherGameCache.game_date == game_date_str,
                    ).first()
                    if existing_cache:
                        total_games += 1
                        continue

                    game_pk = _safe_int(game_df["game_pk"].iloc[0]) if "game_pk" in game_df.columns else 0

                    for _, row in game_df.iterrows():
                        pitch = StatcastPitch(
                            game_pk=_safe_int(row.get("game_pk", game_pk)),
                            game_date=game_date_str,
                            pitcher=pitcher_id,
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
                        pitcher_id=pitcher_id,
                        game_date=game_date_str,
                        game_pk=game_pk,
                        total_pitches=len(game_df),
                    )
                    db.add(cache_record)
                    total_games += 1

                # Mark season as synced
                season_record = PitcherSeason(
                    pitcher_id=pitcher_id,
                    pitcher_name=pitcher_name,
                    season=season,
                    total_games=total_games,
                    total_pitches=len(df),
                )
                db.add(season_record)

            synced += 1
            print(f"OK ({total_games} games)")
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}")

    print(f"\nDone: {synced} synced, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
