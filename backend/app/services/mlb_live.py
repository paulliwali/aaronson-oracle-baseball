"""MLB Stats API integration for live game data.

Uses the MLB Stats API (statsapi.mlb.com) to fetch:
- Today's scheduled/in-progress games
- Live pitch-by-pitch data for a specific game

The data is transformed to match our StatcastPitch schema so existing
prediction models work without modification.
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import statsapi

# Load our pitch type mapping
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PITCH_MAP_PATH = PROJECT_ROOT / "data" / "pitch_map.json"

# MLB Stats API uses different pitch type codes than Statcast in some cases.
# This maps MLB Stats API pitch abbreviations to our simplified types.
# Falls back to pitch_map.json for standard Statcast codes.
MLB_PITCH_TYPE_MAP = None


def _load_pitch_map():
    global MLB_PITCH_TYPE_MAP
    if MLB_PITCH_TYPE_MAP is not None:
        return MLB_PITCH_TYPE_MAP

    with open(PITCH_MAP_PATH) as f:
        MLB_PITCH_TYPE_MAP = json.load(f)
    return MLB_PITCH_TYPE_MAP


def get_todays_games() -> list:
    """Get today's MLB games with status and starting pitcher info.

    Returns list of dicts:
    {
        "game_pk": int,
        "status": str,  # "Pre-Game", "In Progress", "Final", etc.
        "detail_state": str,  # More detailed status
        "home_team": str,
        "away_team": str,
        "home_pitcher": str or None,
        "away_pitcher": str or None,
        "home_score": int,
        "away_score": int,
        "inning": int or None,
        "inning_half": str or None,  # "Top" or "Bottom"
    }
    """
    today = date.today().strftime("%m/%d/%Y")
    schedule = statsapi.schedule(date=today)

    games = []
    for game in schedule:
        games.append({
            "game_pk": game["game_id"],
            "status": game.get("status", "Unknown"),
            "detail_state": game.get("current_inning", ""),
            "home_team": game.get("home_name", ""),
            "away_team": game.get("away_name", ""),
            "home_pitcher": game.get("home_probable_pitcher", ""),
            "away_pitcher": game.get("away_probable_pitcher", ""),
            "home_score": game.get("home_score", 0),
            "away_score": game.get("away_score", 0),
            "inning": game.get("current_inning", None),
            "inning_half": game.get("inning_state", None),
            "summary": game.get("summary", ""),
        })

    return games


def get_live_pitches(game_pk: int, pitcher_name: Optional[str] = None) -> pd.DataFrame:
    """Get pitch-by-pitch data for a live/completed game.

    Fetches the live feed from MLB Stats API and transforms it into a DataFrame
    matching our StatcastPitch schema. If pitcher_name is provided, filters to
    only that pitcher's pitches.

    Returns DataFrame with columns matching fetch_game_stats() output.
    """
    pitch_map = _load_pitch_map()

    # Fetch the full live game feed
    game_data = statsapi.get("game", {"gamePk": game_pk})

    all_plays = game_data.get("liveData", {}).get("plays", {}).get("allPlays", [])
    game_data_info = game_data.get("gameData", {})
    teams = game_data_info.get("teams", {})
    home_team = teams.get("home", {}).get("abbreviation", "")
    away_team = teams.get("away", {}).get("abbreviation", "")
    game_date = game_data_info.get("datetime", {}).get("officialDate", "")
    game_pk_val = game_data.get("gamePk", game_pk)

    pitches = []
    pitch_number = 0

    for play in all_plays:
        matchup = play.get("matchup", {})
        pitcher_info = matchup.get("pitcher", {})
        pitcher_full_name = pitcher_info.get("fullName", "")
        pitcher_id = pitcher_info.get("id", 0)
        batter_info = matchup.get("batter", {})
        batter_id = batter_info.get("id", 0)

        about = play.get("about", {})
        is_top = about.get("isTopInning", True)
        inning = about.get("inning", 1)
        inning_topbot = "Top" if is_top else "Bot"

        result = play.get("result", {})
        event = result.get("event", None)

        play_events = play.get("playEvents", [])
        for pe in play_events:
            if pe.get("isPitch", False):
                pitch_number += 1
                details = pe.get("details", {})
                pitch_type_obj = details.get("type", {})
                pitch_code = pitch_type_obj.get("code", "")
                pitch_name = pitch_type_obj.get("description", "")

                # Map to our simplified types
                simplified = pitch_map.get(pitch_code, None)

                count = pe.get("count", {})
                pitch_data = pe.get("pitchData", {})
                coordinates = pitch_data.get("coordinates", {})

                # Determine score at this point
                # MLB API provides runs in the about section
                home_score = about.get("homeScore", 0)
                away_score = about.get("awayScore", 0)

                pitch_record = {
                    "game_pk": game_pk_val,
                    "game_date": game_date,
                    "pitcher": pitcher_id,
                    "player_name": pitcher_full_name,
                    "batter": batter_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "inning_topbot": inning_topbot,
                    "inning": inning,
                    "pitch_type": pitch_code,
                    "pitch_type_simplified": simplified,
                    "pitch_name": pitch_name,
                    "release_speed": pitch_data.get("startSpeed"),
                    "release_spin_rate": pitch_data.get("breaks", {}).get("spinRate"),
                    "plate_x": coordinates.get("pX"),
                    "plate_z": coordinates.get("pZ"),
                    "balls": count.get("balls", 0),
                    "strikes": count.get("strikes", 0),
                    "outs_when_up": count.get("outs", 0),
                    "pitch_number": pitch_number,
                    "at_bat_number": about.get("atBatIndex", 0) + 1,
                    "events": event if pe == play_events[-1] else None,
                    "description": details.get("description", ""),
                    "type": details.get("code", ""),
                    "home_score": home_score,
                    "away_score": away_score,
                }
                pitches.append(pitch_record)

    if not pitches:
        return pd.DataFrame()

    df = pd.DataFrame(pitches)

    # Filter to specific pitcher if requested
    if pitcher_name:
        df = df[df["player_name"].str.contains(pitcher_name, case=False, na=False)]

    # Drop pitches with unmapped types
    df = df.dropna(subset=["pitch_type_simplified"])

    return df.reset_index(drop=True)
