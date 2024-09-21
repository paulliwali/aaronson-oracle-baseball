import json
from typing import List

import pandas as pd
from flask import Flask, jsonify, render_template, request
from pybaseball import cache, playerid_lookup, statcast_pitcher

DEFAULT_PITCH_VALUE = "fast"
PITCH_GRAM_SIZE = 3

cache.enable()
app = Flask(__name__)

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


def get_player_id(player_name: str) -> int:
    """Get the Statscast player ID given the player name"""

    selected_player_last_name = player_name.split(" ")[1]
    selected_player_first_name = player_name.split(" ")[0]
    print(f"You selected: {selected_player_last_name}, {selected_player_first_name}")

    # Get the statscast playerID
    playerid_lookup_df = playerid_lookup(
        last=selected_player_last_name, first=selected_player_first_name
    )

    return playerid_lookup_df["key_mlbam"].iloc[0]


def map_pitch_type(game_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Map the Statscast pitch type to a simplified version"""
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


@app.route("/")
def index():
    return render_template("index.html", players=players)


@app.route("/get_player_stats", methods=["POST"])
def get_player_stats():
    selected_player = request.form["player"]
    selected_player_id = get_player_id(player_name=selected_player)

    # Get the statcast pitcher data
    selected_player_df = statcast_pitcher(
        start_dt="2023-04-01",
        end_dt="2024-01-01",
        player_id=selected_player_id,
    )

    print(f"Finished fetching {len(selected_player_df)} rows of data")

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

    # Map Statscast pitch type to simpler version
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


if __name__ == "__main__":
    app.run(debug=True)
