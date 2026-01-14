from flask import Flask, jsonify, request, render_template
import threading
import queue

app = Flask(__name__,
            template_folder='../web_game/templates',
            static_folder='../web_game/static')

# =====================================================
# SHARED STATE
# =====================================================
game_state = {
    "connected": False,
    "rounds": 0,
    "initial_cards": [],
    "hit_card": {},
    "stand_cards": [],
    "evt_start_ready": threading.Event(),
    "evt_hit_ready": threading.Event(),
    "evt_stand_ready": threading.Event(),
    "ui_commands": queue.Queue()
}


@app.route("/")
def index():
    return render_template("index.html")


# Update the check_status function:
@app.route("/status", methods=["GET"])
def check_status():
    response = {
        "connected": game_state["connected"],
        "rounds": game_state["rounds"],
        "update": "none",
        "data": None
    }

    # 1. Check for Initial Cards (Start Round)
    if game_state["evt_start_ready"].is_set():
        response["update"] = "start"
        response["data"] = game_state["initial_cards"]
        game_state["evt_start_ready"].clear()

    # 2. Check for Hit Card
    elif game_state["evt_hit_ready"].is_set():
        response["update"] = "hit"
        response["data"] = game_state["hit_card"]
        game_state["evt_hit_ready"].clear()

    # 3. Check for Stand Cards (End Round)
    elif game_state["evt_stand_ready"].is_set():
        response["update"] = "stand"
        response["data"] = game_state["stand_cards"]
        game_state["evt_stand_ready"].clear()

    return jsonify(response)

@app.route("/connect", methods=["POST"])
def initiate_game():
    try:
        data = request.get_json()
        rounds = data.get("rounds", 1)
        game_state["rounds"] = rounds
        game_state["connected"] = True
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# === Non-Blocking Command Endpoints ===
# These just tell Client.py to do something. They don't wait for the result.
# The result will be picked up by the /status poller above.

@app.route("/start", methods=["POST"])
def start_cmd():
    return jsonify({"status": "waiting_for_client"})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'


@app.route("/hit", methods=["POST"])
def hit_cmd():
    game_state["ui_commands"].put("Hit")
    return jsonify({"status": "command_sent"})


@app.route("/stand", methods=["POST"])
def stand_cmd():
    game_state["ui_commands"].put("Stand")
    return jsonify({"status": "command_sent"})


def run_api_thread():
    app.run(port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_api_thread()