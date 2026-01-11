import struct
import sys
import socket
import json

with open("../config.json", "r") as f:
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
    name_to_bytes = name.encode('utf-8')
    packed_name = struct.pack('32s', name_to_bytes)
    return packed_name


def generate_request_msg(magic_cookie, msg_type, rounds, client_name):
    packet_msg = struct.pack('! I B B 32s',
                             magic_cookie,
                             msg_type,
                             rounds,
                             client_name)
    return packet_msg


def check_cookie(magic_cookie):
    return magic_cookie == int(config_params["magic_cookie"], 16)


def recv_exact(sock, size):
    data = b''
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def recv_payload(sock):
    data = recv_exact(sock, 9)
    if not data:
        return None

    magic, msg_type, result, rank, shape = struct.unpack('!IBBHB', data)
    return magic, msg_type, result, rank, shape


def ask_player_decision():
    while True:
        decision = input("Hit or Stand? ").strip().lower()
        if decision == "hit":
            return "Hit"
        if decision == "stand":
            return "Stand"
        print("Please type 'Hit' or 'Stand'")


def result_to_string(result):
    if result == 0x1:
        return "Tie 🤝"
    if result == 0x2:
        return "You lost ❌"
    if result == 0x3:
        return "You won 🎉"
    return None

def run_server(name):
    """
    initialize server
    """
    # 1. Create and bind the socket manually
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', 13122))

    client_name = generate_client_name(name)

    # Send TCP request: ack -> syn + ack
    def connect_to_server(server_ip, server_port, magic_cookie):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_ip, server_port))
        rounds = int(input("Enter number of rounds: "))
        request_msg = generate_request_msg(magic_cookie, int(config_params["msg_type_request"], 16), rounds, client_name)
        sock.sendall(request_msg)
        return sock, rounds

    while True:
        print("got here")
        data, addr = sock.recvfrom(39)
        print(f"Received {len(data)} bytes from {addr}")

        magic_cookie, msg_type, server_port, server_name = struct.unpack('! I B H 32s', data)
        server_name = server_name.rstrip(b'\x00').decode('utf-8')
        print(f"Server: {server_name}, TCP port: {server_port}")
        if not check_cookie(magic_cookie):
            print(magic_cookie)
            continue
        game_socket, rounds = connect_to_server(addr[0], server_port, magic_cookie)

        # play game logic
        print("send request")

        player_cards = []
        dealer_card = None

        for round_num in range(rounds):
            print(f"\n=== Round {round_num + 1} ===")
            print("Waiting for initial cards...")


            for i in range(3):
                payload = recv_payload(game_socket)
                if payload is None:
                    print("Server disconnected")
                    break

                magic, msg_type, result, rank, shape = payload

                card_str = card_to_string(rank, shape)

                if i < 2:
                    player_cards.append(card_str)
                    print(f"Player card {i + 1}: {card_str}")
                else:
                    dealer_card = card_str
                    print(f"Dealer shows: {card_str}")

            round_over = False

            while not round_over:
                decision = ask_player_decision()
                game_socket.sendall(decision.encode())

                if decision == "Hit":
                    payload = recv_payload(game_socket)
                    if payload is None:
                        print("Server disconnected")
                        return

                    magic, msg_type, result, rank, shape = payload
                    print("Received card:", card_to_string(rank, shape))

                    if result != 0x0:
                        print(result_to_string(result))
                        round_over = True

                    # ===== STAND =====
                else:  # Stand
                    while True:
                        payload = recv_payload(game_socket)
                        if payload is None:
                            print("Server disconnected")
                            return

                        magic, msg_type, result, rank, shape = payload
                        print("Dealer card:", card_to_string(rank, shape))

                        if result != 0x0:
                            print(result_to_string(result))
                            round_over = True
                            break


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise "Invalid Arguments"
    name = sys.argv[1]
    run_server(name)
