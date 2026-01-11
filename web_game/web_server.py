import socket
import struct
import json
from flask import Flask, jsonify, request, render_template

# ===== Load protocol config =====
with open("../config.json") as f:
    config = json.load(f)

MAGIC = int(config["magic_cookie"], 16)
MSG_OFFER = int(config["msg_type_offer"], 16)
MSG_REQUEST = int(config["msg_type_request"], 16)

# ===== Flask =====
app = Flask(__name__)

game_sock = None   # TCP socket to your game server
connected = False

# ===== UDP discovery (same as your Client) =====
def discover_server():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("", 13122))

    data, addr = udp.recvfrom(39)
    magic, msg_type, tcp_port, name = struct.unpack("!IBH32s", data)

    if magic != MAGIC or msg_type != MSG_OFFER:
        return None

    return addr[0], tcp_port


# ===== Receive exact bytes =====
def recv_exact(sock, size):
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def recv_payload():
    data = recv_exact(game_sock, 9)
    if not data:
        return None

    magic, msg_type, result, rank, shape = struct.unpack("!IBBHB", data)
    return {
        "rank": rank,
        "shape": shape,
        "result": result
    }


# ===== Routes =====

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/connect", methods=["POST"])
def connect():
    global game_sock, connected

    if connected:
        return jsonify({"ok": True})

    server = discover_server()
    if not server:
        return jsonify({"error": "No server found"}), 500

    ip, port = server
    game_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    game_sock.connect((ip, port))

    rounds = request.json.get("rounds", 1)
    name = b"WEB_PLAYER".ljust(32, b"\x00")

    req = struct.pack("!IBB32s", MAGIC, MSG_REQUEST, rounds, name)
    game_sock.sendall(req)

    connected = True
    return jsonify({"ok": True})


@app.route("/start", methods=["POST"])
def start():
    cards = []
    for _ in range(3):
        payload = recv_payload()
        cards.append(payload)
    return jsonify(cards)


@app.route("/hit", methods=["POST"])
def hit():
    game_sock.sendall(b"Hit")
    payload = recv_payload()
    return jsonify(payload)


@app.route("/stand", methods=["POST"])
def stand():
    game_sock.sendall(b"Stand")
    cards = []

    while True:
        payload = recv_payload()
        cards.append(payload)
        if payload["result"] != 0:
            break

    return jsonify(cards)


if __name__ == "__main__":
    app.run(debug=True)
