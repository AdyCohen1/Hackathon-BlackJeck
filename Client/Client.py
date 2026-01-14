import sys
import os
import socket
import struct
import json
import threading
import queue
import time
import urllib.request  # <--- Added for sending API requests
import urllib.error

# ==============================================================================
# 1. SETUP PATHS & IMPORT WEB SERVER
# ==============================================================================
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Robustly find 'web_game' (Sibling or Child)
    possible_paths = [
        os.path.abspath(os.path.join(current_dir, '../web_game')),
        os.path.abspath(os.path.join(current_dir, 'web_game'))
    ]

    web_game_path = None
    for path in possible_paths:
        if os.path.exists(os.path.join(path, 'web_server.py')):
            web_game_path = path
            break

    if not web_game_path:
        raise FileNotFoundError("Could not find 'web_game/web_server.py'")

    if web_game_path not in sys.path:
        sys.path.insert(0, web_game_path)

    import web_server  #

except Exception as e:
    print(f"\n[ERROR] Failed to load web_server: {e}\n")
    sys.exit(1)

# ==============================================================================
# 2. SHARED QUEUE & PATCH LOGIC
# ==============================================================================
input_queue = queue.Queue()


def patch_web_server():
    """
    Hooks the /connect endpoint.
    Logic:
    - If request comes from Browser: Put in Queue (Wake up Client), Update State.
    - If request comes from Terminal: Just Update State (Don't Queue).
    """
    from flask import request, jsonify

    # We store the original logic to replicate its behavior (prints/state)
    # or we can just rewrite it here since it's simple.
    def hooked_initiate_game():
        try:
            data = request.get_json()
            rounds = data.get("rounds", 1)

            # Check source to prevent feedback loop
            source = request.headers.get("X-Source", "Browser")

            if source == "Browser":
                # Came from Web UI -> Wake up the Client thread
                input_queue.put(("WEB", rounds))
                print(f"[Web API] UI Request: Starting {rounds} rounds.")
            else:
                # Came from Terminal -> Client already knows, just sync state
                print(f"[Web API] Sync Request: Updating state to {rounds} rounds.")

            # --- Original Server Logic (Updates State) ---
            web_server.game_state["rounds"] = rounds
            web_server.game_state["connected"] = True
            # ---------------------------------------------

            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # Apply Hook
    web_server.app.view_functions['initiate_game'] = hooked_initiate_game


patch_web_server()

# ==============================================================================
# 3. CLIENT LOGIC
# ==============================================================================

with open("../config.json", "r") as f:  #
    config_params = json.load(f)

SHAPES = ["Heart", "Diamond", "Club", "Spade"]


def card_to_string(rank, shape):
    if rank == 1:
        rank_str = "A"
    elif rank == 11:
        rank_str = "J"
    elif rank == 12:
        rank_str = "Q"
    elif rank == 13:
        rank_str = "K"
    else:
        rank_str = str(rank)
    return f"{rank_str} of {SHAPES[shape]}"


def generate_client_name(name):
    return struct.pack('32s', name.encode('utf-8'))


def generate_request_msg(magic_cookie, msg_type, rounds, client_name):
    return struct.pack('! I B B 32s', magic_cookie, msg_type, rounds, client_name)


def check_cookie(magic_cookie):
    return magic_cookie == int(config_params["magic_cookie"], 16)


def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk: return None
        data += chunk
    return data


def recv_payload(sock):
    data = recv_exact(sock, 9)
    if not data: return None
    magic, msg_type, result, rank, shape = struct.unpack('!IBBHB', data)
    return magic, msg_type, result, rank, shape



def result_to_string(result):
    if result == 0x1: return "Tie 🤝"
    if result == 0x2: return "You lost ❌"
    if result == 0x3: return "You won 🎉"
    return None


def run_server(name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 13122))

    client_name = generate_client_name(name)
    web_server_started = False

    def ask_player_decision():
        print("Action: (Type 'hit'/'stand' or click in Browser)...")


        while True:
            # --- 1. Check Web UI ---
            # We wrap this in a try-except to prevent crashes if web_server isn't ready
            try:
                if web_server_started:
                    # Debug print to prove we are checking (remove later if too spammy)
                    # print("[DEBUG] Checking Web Queue...")

                    if not web_server.game_state["ui_commands"].empty():
                        cmd = web_server.game_state["ui_commands"].get()
                        print(f"[Web UI] Received command: {cmd}")
                        return cmd
                else:
                    # If this prints, your web server thread hasn't started yet
                    # print("[DEBUG] Web server flag is False")
                    pass
            except Exception as e:
                print(f"[ERROR] Web Queue check failed: {e}")
            # --- 2. Check Terminal ---
            if not input_queue.empty():
                print("another one")

                data = input_queue.get()
                print(f"[DEBUG] Terminal Queue item: {data}")

                source, cmd = data
                if isinstance(cmd, str) and cmd.lower() in ["hit", "stand"]:
                    return cmd.capitalize()
                else:
                    print(f"[DEBUG] Ignored invalid input: '{cmd}'")

            time.sleep(0.1)

    # -------------------------------------------------------------
    # HELPER: Sync Terminal Input to Web Server
    # -------------------------------------------------------------
    def sync_to_web_server(rounds):
        """Sends a POST request to the local Flask server to update its state."""
        try:
            url = "http://127.0.0.1:5000/connect"
            data = json.dumps({"rounds": rounds}).encode('utf-8')

            # Send with custom header so the server knows NOT to queue it back
            req = urllib.request.Request(url, data=data, headers={
                'Content-Type': 'application/json',
                'X-Source': 'Terminal'
            })

            with urllib.request.urlopen(req) as response:
                if response.getcode() == 200:
                    pass  # Success
        except Exception as e:
            print(f"[Warning] Could not sync to Web Server: {e}")

    # -------------------------------------------------------------
    # CONNECT FUNCTION
    # -------------------------------------------------------------
    def connect_to_server(server_ip, server_port, magic_cookie):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))

        # 1. Listen for Terminal Input
        def terminal_input_listener():
            while True:
                try:
                    user_text = sys.stdin.readline()
                    if user_text:
                        input_queue.put(("TERMINAL", user_text.strip()))
                except:
                    break

        t_input = threading.Thread(target=terminal_input_listener)
        t_input.daemon = True
        t_input.start()
        print("Enter number of rounds: ", end='', flush=True)

        # 2. Wait for Input (Blocking)
        source, raw_value = input_queue.get()

        try:
            rounds = int(raw_value)
        except ValueError:
            print(f"Invalid input '{raw_value}', defaulting to 3")
            rounds = 3

        # 3. Handle Source
        if source == "WEB":
            print(f"{rounds} (Received via Web Interface)")
        else:
            # TERMINAL -> Send API Request to Web Server
            sync_to_web_server(rounds)

        request_msg = generate_request_msg(magic_cookie, int(config_params["msg_type_request"], 16), rounds,
                                           client_name)
        sock.sendall(request_msg)
        return sock, rounds

    while True:
        print("Listening for offer requests...")
        data, addr = sock.recvfrom(39)

        magic_cookie, msg_type, server_port, server_name = struct.unpack('! I B H 32s', data)
        server_name = server_name.rstrip(b'\x00').decode('utf-8')
        print(f"Server found: {server_name}, TCP port: {server_port}")

        if not check_cookie(magic_cookie):
            continue

        # === START FLASK THREAD ===
        if not web_server_started:
            try:
                import logging
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)
                web_server.app.logger.disabled = True

                t = threading.Thread(target=web_server.run_api_thread)
                t.daemon = True
                t.start()
                time.sleep(1)

                print(f"[Client] Web Control: http://127.0.0.1:5000\n")
                web_server_started = True
            except Exception as e:
                print(f"[Error] Failed to start web server: {e}")

        game_socket, rounds = connect_to_server(addr[0], server_port, magic_cookie)

        print("Sending request...")
        player_cards = []
        initial_cards = []
        for round_num in range(rounds):

            print(f"\n=== Round {round_num + 1} ===")
            print("Waiting for initial cards...")

            # 1. Create a fresh list for this round
            web_initial_cards = []

            for i in range(3):
                payload = recv_payload(game_socket)
                if not payload:
                    print("Server disconnected")
                    break

                magic, msg_type, result, rank, shape = payload
                card_str = card_to_string(rank, shape)

                # 2. Format data for Web (Use Integers, don't parse string!)
                # app.js needs integers to find the image files (e.g. 1_of_hearts.png)
                card_data = {
                    "rank": rank,
                    "shape": shape,
                    "result": result
                }
                web_initial_cards.append(card_data)

                if i < 2:
                    player_cards.append(card_str)
                    print(f"Player card {i + 1}: {card_str}")
                else:
                    print(f"Dealer shows: {card_str}")

            # 3. CRITICAL FIX: Update State AND Signal the Event
            if web_server_started:
                web_server.game_state["initial_cards"] = web_initial_cards

                # This stops the 503 Error! It tells Flask "Data is ready!"
                web_server.game_state["evt_start_ready"].set()

            round_over = False
            while not round_over:
                decision = ask_player_decision()
                game_socket.sendall(decision.encode())

                if decision == "Hit":
                    payload = recv_payload(game_socket)
                    if not payload: break

                    magic, msg_type, result, rank, shape = payload
                    print("Received card:", card_to_string(rank, shape))


                    # --- SYNC HIT TO WEB ---
                    if web_server_started:
                        # 1. Format the single card
                        card_data = {
                            "rank": rank,
                            "shape": shape,
                            "result": result
                        }
                        # 2. Update state and trigger event
                        web_server.game_state["hit_card"] = card_data
                        web_server.game_state["evt_hit_ready"].set()


                    # -----------------------

                    if result != 0x0:
                        print(result_to_string(result))
                        round_over = True
                else:
                    # Stand
                    web_dealer_cards = []  # Collect all dealer cards here

                    while True:
                        payload = recv_payload(game_socket)
                        if not payload: break

                        magic, msg_type, result, rank, shape = payload
                        print("Dealer card:", card_to_string(rank, shape))

                        # --- COLLECT CARD FOR WEB ---
                        card_data = {
                            "rank": rank,
                            "shape": shape,
                            "result": result
                        }
                        web_dealer_cards.append(card_data)
                        # ----------------------------

                        if result != 0x0:
                            print(result_to_string(result))
                            round_over = True

                            # --- SYNC STAND TO WEB (Full Sequence) ---
                            if web_server_started:
                                web_server.game_state["stand_cards"] = web_dealer_cards
                                web_server.game_state["evt_stand_ready"].set()
                            # -----------------------------------------

                            break




if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python Client.py <name>")
    else:
        name = sys.argv[1]
        run_server(name)