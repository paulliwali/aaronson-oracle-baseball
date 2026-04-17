"""Fast bulk download: fetch all Statcast data by month, save every starter.

Auto-discovers starters from the Statcast feed — any pitcher meeting
MIN_PITCHES_PER_GAME on any date gets a per-season CSV. `pitchers.json` is
used only for the `seasons` field; the curated roster is ignored.

Usage: uv run python training/bulk_download.py
"""

import json
import re
import time
from pathlib import Path

import pandas as pd
from pybaseball import statcast

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training"
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"
PITCHERS_PATH = Path(__file__).parent / "pitchers.json"

MIN_PITCHES_PER_GAME = 60


def _safe_name(raw: str) -> str:
    """Normalize a player_name ("Last, First") into a filesystem-safe slug."""
    parts = raw.split(", ", 1)
    display = f"{parts[1]} {parts[0]}" if len(parts) == 2 else raw
    slug = display.strip().lower().replace(" ", "_")
    # Strip anything that isn't alnum/underscore/hyphen/dot to avoid surprises
    return re.sub(r"[^a-z0-9_\-.]", "", slug) or "unknown"


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(PITCHERS_PATH) as f:
        seasons = json.load(f)["seasons"]

    with open(PITCH_MAP_PATH) as f:
        pitch_map = json.load(f)

    print(f"Auto-discovering starters across seasons {seasons}")

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
        print(f"\n{'='*60}")
        print(f"Season {season}")
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

        # Apply pitch mapping (drops pitches without a simplified label)
        all_data["pitch_type_simplified"] = all_data["pitch_type"].map(pitch_map)
        all_data = all_data.dropna(subset=["pitch_type_simplified", "pitcher"])

        # Per-pitcher: keep only the dates where they threw >= MIN_PITCHES_PER_GAME
        # (this is how we auto-identify starter appearances without a roster file).
        saved = 0
        skipped_existing = 0
        for pid, pdf in all_data.groupby("pitcher"):
            game_counts = pdf.groupby("game_date").size()
            starter_dates = game_counts[game_counts >= MIN_PITCHES_PER_GAME].index
            pdf = pdf[pdf["game_date"].isin(starter_dates)]

            if pdf.empty:
                continue

            raw_name = pdf["player_name"].iloc[0] if "player_name" in pdf.columns else str(pid)
            safe_name = _safe_name(raw_name)
            out_path = DATA_DIR / f"{safe_name}_{season}.csv"

            if out_path.exists():
                skipped_existing += 1
                continue

            pdf.to_csv(out_path, index=False)
            n_games = pdf["game_date"].nunique()
            print(f"    {raw_name}: {len(pdf)} pitches, {n_games} games -> {out_path.name}")
            saved += 1

        print(f"  Saved {saved} new pitcher-season files, skipped {skipped_existing} already-present")

    # Summary
    total_files = len(list(DATA_DIR.glob("*.csv")))
    total_lines = sum(1 for f in DATA_DIR.glob("*.csv") for _ in open(f)) - total_files  # subtract headers
    print(f"\nDone! {total_files} CSV files, ~{total_lines:,} total pitches")


if __name__ == "__main__":
    main()
