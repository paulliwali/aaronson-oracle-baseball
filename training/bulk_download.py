"""Fast bulk download: fetch all Statcast data by month, filter to our pitchers.

Much faster than per-pitcher API calls since statcast() fetches everything at once.

Usage: uv run python training/bulk_download.py
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
from pybaseball import statcast

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training"
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"
PITCHERS_PATH = Path(__file__).parent / "pitchers.json"

MIN_PITCHES_PER_GAME = 60


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(PITCHERS_PATH) as f:
        data = json.load(f)
    pitchers = data["pitchers"]
    seasons = data["seasons"]
    pitcher_ids = {p["mlbam_id"] for p in pitchers}
    id_to_name = {p["mlbam_id"]: p["name"] for p in pitchers}

    with open(PITCH_MAP_PATH) as f:
        pitch_map = json.load(f)

    # Check which files already exist
    existing = set()
    for p in pitchers:
        safe_name = p["name"].replace(" ", "_").lower()
        for season in seasons:
            path = DATA_DIR / f"{safe_name}_{season}.csv"
            if path.exists():
                existing.add((p["mlbam_id"], season))

    print(f"{len(existing)} pitcher-seasons already downloaded, skipping those")

    # Months to fetch per season
    months = [
        ("03-01", "03-31"),
        ("04-01", "04-30"),
        ("05-01", "05-31"),
        ("06-01", "06-30"),
        ("07-01", "07-31"),
        ("08-01", "08-31"),
        ("09-01", "09-30"),
        ("10-01", "10-31"),
        ("11-01", "11-30"),
    ]

    for season in seasons:
        # Check if all pitchers already have this season
        needed = [pid for pid in pitcher_ids if (pid, season) not in existing]
        if not needed:
            print(f"\n{season}: all pitchers already downloaded, skipping")
            continue

        print(f"\n{'='*60}")
        print(f"Season {season}: need data for {len(needed)} pitchers")
        print(f"{'='*60}")

        season_frames = []
        for start_sfx, end_sfx in months:
            start_dt = f"{season}-{start_sfx}"
            end_dt = f"{season}-{end_sfx}"

            print(f"  Fetching {start_dt} to {end_dt}...")
            try:
                df = statcast(start_dt=start_dt, end_dt=end_dt)
                if df is not None and not df.empty:
                    season_frames.append(df)
                    print(f"    Got {len(df):,} pitches")
                else:
                    print(f"    No data")
            except Exception as e:
                print(f"    ERROR: {e}")
                continue
            time.sleep(2)

        if not season_frames:
            print(f"  No data for {season}")
            continue

        all_data = pd.concat(season_frames, ignore_index=True)
        all_data = all_data.copy()
        print(f"  Total: {len(all_data):,} pitches for {season}")

        # Filter to our pitchers
        pitcher_data = all_data[all_data["pitcher"].isin(pitcher_ids)]
        print(f"  Our pitchers: {len(pitcher_data):,} pitches, {pitcher_data['pitcher'].nunique()} pitchers")

        # Apply pitch mapping
        pitcher_data = pitcher_data.copy()
        pitcher_data["pitch_type_simplified"] = pitcher_data["pitch_type"].map(pitch_map)
        pitcher_data = pitcher_data.dropna(subset=["pitch_type_simplified"])

        # Save per-pitcher CSVs
        saved = 0
        for pid, pdf in pitcher_data.groupby("pitcher"):
            if (pid, season) in existing:
                continue

            # Filter to starter appearances
            game_counts = pdf.groupby("game_date").size()
            starter_dates = game_counts[game_counts >= MIN_PITCHES_PER_GAME].index
            pdf = pdf[pdf["game_date"].isin(starter_dates)]

            if pdf.empty:
                continue

            name = id_to_name.get(pid, str(pid))
            safe_name = name.replace(" ", "_").lower()
            out_path = DATA_DIR / f"{safe_name}_{season}.csv"
            pdf.to_csv(out_path, index=False)
            n_games = pdf["game_date"].nunique()
            print(f"    {name}: {len(pdf)} pitches, {n_games} games -> {out_path.name}")
            saved += 1

        print(f"  Saved {saved} new pitcher-season files for {season}")

    # Summary
    total_files = len(list(DATA_DIR.glob("*.csv")))
    total_lines = sum(1 for f in DATA_DIR.glob("*.csv") for _ in open(f)) - total_files  # subtract headers
    print(f"\nDone! {total_files} CSV files, ~{total_lines:,} total pitches")


if __name__ == "__main__":
    main()
