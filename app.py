from flask import Flask, render_template, request, jsonify
from pybaseball import cache, statcast_pitcher, playerid_lookup

cache.enable()
app = Flask(__name__)


# List of baseball pitchers
players = ["Logan Webb", "Sandy Alcantara", "Alek Manoah"]


def get_player_id(player_name: str) -> int:
    selected_player_last_name = player_name.split(" ")[1]
    selected_player_first_name = player_name.split(" ")[0]
    print(f"You selected: {selected_player_last_name}, {selected_player_first_name}")

    # Get the statscast playerID
    playerid_lookup_df = playerid_lookup(
        last=selected_player_last_name, first=selected_player_first_name
    )

    return playerid_lookup_df["key_mlbam"].iloc[0]


@app.route("/")
def index():
    return render_template("index.html", players=players)


@app.route("/get_player_stats", methods=["POST"])
def get_player_stats():
    selected_player = request.form["player"]
    selected_player_id = get_player_id(player_name=selected_player)

    # Get the statcast pitcher data
    selected_player_df = statcast_pitcher(
        start_dt="2024-03-01",
        end_dt="2024-05-01",
        player_id=selected_player_id,
    )

    print(f"Finished fetching {len(selected_player_df)} rows of data")

    return jsonify(
        {
            "selected_player": selected_player,
            "game_dates": list(selected_player_df.game_date.unique()),
        }
    )


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

    return jsonify({"game_stats": game_stats_df.to_json(orient="records")})


if __name__ == "__main__":
    app.run(debug=True)
