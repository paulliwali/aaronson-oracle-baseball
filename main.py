"""Main entry point to the app"""

import os
import json
import signal
import redis
from typing import List

import pandas as pd
from flask import Flask, jsonify, render_template, request
from pybaseball import playerid_lookup, statcast_pitcher
import markdown

from constants import (
    CACHE_FILE_FORMAT,
    DEFAULT_PITCH_VALUE,
    PITCH_GRAM_SIZE,
    START_DT,
    END_DT,
)

app = Flask(__name__)

# Connect to redis
redis_url = os.getenv("REDIS_URL")
cache = redis.StrictRedis.from_url(redis_url, decode_responses=True)


def read_readme() -> str:
    """Parse the content of the readme markdown file"""
    with open("README.md", "r") as file:
        content = file.read()
    return markdown.markdown(content)


def get_player_id(player_name: str) -> int:
    """Get the Statcast player ID given the player name"""

    selected_player_last_name = player_name.split(" ")[1]
    selected_player_first_name = player_name.split(" ")[0]
    print(f"You selected: {selected_player_last_name}, {selected_player_first_name}")

    # Get the Statcast playerID
    playerid_lookup_df = playerid_lookup(
        last=selected_player_last_name, first=selected_player_first_name
    )

    return playerid_lookup_df["key_mlbam"].iloc[0]


def map_pitch_type(game_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Map the Statcast pitch type to a simplified version"""
    with open("data/pitch_map.json", "r") as f:
        pitch_map = json.load(f)

    game_stats_df["pitch_type_simplified"] = game_stats_df.loc[:, "pitch_type"].replace(
        pitch_map
    )

    return game_stats_df


def update_model(model: dict, pitch_gram: str, next_pitch: str) -> None:
    """Update the model by either incrementing the value of a existing pitch_gram or
    initializing it with a value of 1
    """
    if pitch_gram in model:
        # Update the value
        model[pitch_gram][next_pitch] = model[pitch_gram].get(next_pitch, 0) + 1
    else:
        # Initialize the value
        model[pitch_gram] = {next_pitch: 1}


def make_prediction(model: dict, pitch_gram: str) -> str:
    """Make a prediction with the highest value for the next possible pitch
    or use the default value if it doesn't exist"""
    if pitch_gram in model:
        next_possible_pitch = model[pitch_gram]
        return max(next_possible_pitch, key=next_possible_pitch.get)

    else:
        return DEFAULT_PITCH_VALUE


def create_valid_pitch_gram(pitches: List[str], pitch_gram_size: int) -> str:
    """Create a valid pitch gram"""
    if len(pitches) == pitch_gram_size:
        return "".join(p for p in pitches)


def predict_pitch_type(game_stats_df: pd.DataFrame, gram_size: int) -> list:
    """Iterate through the pitches and make predictions while updating the model"""
    predicted_pitch = []
    model = {}

    for i in range(len(game_stats_df)):
        past_pitches = (
            game_stats_df["pitch_type_simplified"].iloc[i - gram_size : i].to_list()
        )

        next_pitch = game_stats_df["pitch_type_simplified"].iloc[i]
        pitch_gram = create_valid_pitch_gram(
            pitches=past_pitches, pitch_gram_size=PITCH_GRAM_SIZE
        )

        # Make the prediction
        predicted_pitch.append(make_prediction(model=model, pitch_gram=pitch_gram))

        # Update the model
        update_model(model=model, pitch_gram=pitch_gram, next_pitch=next_pitch)

    return predicted_pitch


def naive_predict_pitch_type(game_stats_df: pd.DataFrame) -> list:
    """Naïve algorithm that always predicts the default pitch type."""
    predicted_pitch = [DEFAULT_PITCH_VALUE] * len(game_stats_df)
    return predicted_pitch


def fetch_and_cache_player_stats(
    player_id: int, start_dt: str, end_dt: str
) -> pd.DataFrame:
    """Fetch and cache the player stats, read from cache if its available"""
    cache_key = CACHE_FILE_FORMAT.format(
        player_id=player_id, start_dt=start_dt, end_dt=end_dt
    )

    cache_data = cache.get(cache_key)
    if cache_data:
        return pd.read_json(cache_data)

    selected_player_df = statcast_pitcher(
        player_id=player_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    cache.set(cache_key, selected_player_df.to_json(orient="records"), ex=86400)
    return selected_player_df


@app.route("/")
def index():
    readme_content = read_readme()

    # List of baseball pitchers
    players = [
        "Logan Webb",
        "Corbin Burnes",
        "Zac Gallen",
        "Gerrit Cole",
        "Blake Snell",
        "Zack Wheeler",
        "Kodai Senga",
    ]

    return render_template("index.html", readme_content=readme_content, players=players)


@app.route("/get_player_stats", methods=["POST"])
def get_player_stats():
    selected_player = request.form["player"]
    selected_player_id = get_player_id(player_name=selected_player)

    # Get the Statcast pitcher data
    selected_player_df = fetch_and_cache_player_stats(
        player_id=selected_player_id,
        start_dt=START_DT,
        end_dt=END_DT,
    )

    return jsonify(
        {
            "selected_player": selected_player,
            "game_dates": list(selected_player_df.game_date.unique()),
        }
    )


def calculate_rolling_accuracy(is_correct_series: pd.Series) -> list:
    """Calculate rolling accuracy over the series."""
    correct_count = 0
    rolling_accuracy = []

    for i, is_correct in enumerate(is_correct_series, start=1):
        if is_correct:
            correct_count += 1
        rolling_accuracy.append(correct_count / i)

    return rolling_accuracy


@app.route("/get_game_stats", methods=["POST"])
def get_game_stats():
    selected_player = request.form["selected_player"]
    print(selected_player)
    selected_player_id = get_player_id(player_name=selected_player)
    selected_game_date = request.form["game_date"]

    # Get the statcast pitcher data
    game_stats_df = statcast_pitcher(
        start_dt=selected_game_date,
        end_dt=selected_game_date,
        player_id=selected_player_id,
    )
    print(f"Finished fetching {len(game_stats_df)} rows of single-game data")

    # Map Statcast pitch type to simpler version
    game_stats_df = map_pitch_type(game_stats_df=game_stats_df)

    # Predict with the algorithm
    game_stats_df["pitch_type_predicted"] = predict_pitch_type(
        game_stats_df=game_stats_df, gram_size=PITCH_GRAM_SIZE
    )
    game_stats_df["is_correct"] = (
        game_stats_df["pitch_type_predicted"] == game_stats_df["pitch_type_simplified"]
    )
    model_accuracy = round(sum(game_stats_df["is_correct"]) / len(game_stats_df), 4)

    # Predict with the naive algorithm
    game_stats_df["pitch_type_naive"] = naive_predict_pitch_type(
        game_stats_df=game_stats_df
    )
    game_stats_df["is_naive_correct"] = (
        game_stats_df["pitch_type_naive"] == game_stats_df["pitch_type_simplified"]
    )
    naive_accuracy = round(
        sum(game_stats_df["is_naive_correct"]) / len(game_stats_df), 4
    )

    # Calculate rolling accuracies
    model_rolling_accuracy = calculate_rolling_accuracy(game_stats_df["is_correct"])
    naive_rolling_accuracy = calculate_rolling_accuracy(
        game_stats_df["is_naive_correct"]
    )

    return jsonify(
        {
            "game_stats": game_stats_df.to_json(orient="records"),
            "model_accuracy": model_accuracy,
            "naive_accuracy": naive_accuracy,
            "model_rolling_accuracy": model_rolling_accuracy,
            "naive_rolling_accuracy": naive_rolling_accuracy,
        }
    )


@app.route("/stopServer", methods=["GET"])
def stopServer():
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"success": True, "message": "Server is shutting down..."})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
