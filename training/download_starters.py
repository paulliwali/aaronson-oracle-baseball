"""Download Statcast data for starting pitchers across multiple seasons."""

import json
import time
from pathlib import Path

import pandas as pd
from pybaseball import playerid_lookup, statcast_pitcher


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training"
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"
PITCHERS_PATH = Path(__file__).parent / "pitchers.json"

MIN_PITCHES_PER_GAME = 60  # filter to starter appearances
API_DELAY_SECONDS = 5


def load_pitch_map():
    with open(PITCH_MAP_PATH) as f:
        return json.load(f)


def load_pitchers():
    with open(PITCHERS_PATH) as f:
        data = json.load(f)
    return data["pitchers"], data["seasons"]


def get_player_id(first: str, last: str) -> int:
    df = playerid_lookup(last=last, first=first)
    if df.empty:
        raise ValueError(f"Player not found: {first} {last}")
    return int(df["key_mlbam"].iloc[0])


def download_pitcher_season(pitcher: dict, season: int, pitch_map: dict):
    """Download and save one pitcher-season CSV. Returns path or None if skipped."""
    safe_name = pitcher["name"].replace(" ", "_").lower()
    out_path = DATA_DIR / f"{safe_name}_{season}.csv"

    if out_path.exists():
        print(f"  Skip (exists): {out_path.name}")
        return out_path

    try:
        player_id = get_player_id(pitcher["first"], pitcher["last"])
    except ValueError as e:
        print(f"  ERROR: {e}")
        return None

    start_dt = f"{season}-03-01"
    end_dt = f"{season}-11-30"

    print(f"  Fetching {pitcher['name']} {season} (ID: {player_id})...")
    try:
        df = statcast_pitcher(
            start_dt=start_dt, end_dt=end_dt, player_id=player_id
        )
    except Exception as e:
        print(f"  ERROR fetching: {e}")
        return None

    if df.empty:
        print(f"  No data for {pitcher['name']} {season}")
        return None

    # Defragment the DataFrame (pybaseball returns fragmented frames)
    df = df.copy()

    # Apply pitch type mapping
    df["pitch_type_simplified"] = df["pitch_type"].map(pitch_map)
    # Drop rows with unmapped pitch types
    df = df.dropna(subset=["pitch_type_simplified"])

    # Filter to starter appearances (>60 pitches in a game)
    game_pitch_counts = df.groupby("game_date").size()
    starter_dates = game_pitch_counts[game_pitch_counts >= MIN_PITCHES_PER_GAME].index
    df = df[df["game_date"].isin(starter_dates)]

    if df.empty:
        print(f"  No starter appearances for {pitcher['name']} {season}")
        return None

    n_games = df["game_date"].nunique()
    print(f"  Saved: {len(df)} pitches across {n_games} starts")
    df.to_csv(out_path, index=False)
    return out_path


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pitchers, seasons = load_pitchers()
    pitch_map = load_pitch_map()

    total = len(pitchers) * len(seasons)
    done = 0
    skipped = 0
    errors = 0

    for pitcher in pitchers:
        print(f"\n{'='*50}")
        print(f"Pitcher: {pitcher['name']}")
        print(f"{'='*50}")

        for season in seasons:
            result = download_pitcher_season(pitcher, season, pitch_map)
            done += 1

            if result is None:
                errors += 1
            elif result.exists():
                skipped += 1  # includes both pre-existing and newly saved

            # Rate limit API calls
            if done < total:
                print(f"  Waiting {API_DELAY_SECONDS}s before next request...")
                time.sleep(API_DELAY_SECONDS)

    print(f"\n{'='*50}")
    print(f"Done: {done}/{total} pitcher-seasons processed")
    print(f"Errors: {errors}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
