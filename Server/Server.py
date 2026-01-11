import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socket import socket
import struct
from scapy.all import *
from scapy.layers.inet import UDP, IP
import threading
from GameLogic.Game import Game

# protocol / payload constants
ROUND_NOT_OVER = 0x0
RESULT_TIE = 0x1
RESULT_LOSS = 0x2
RESULT_WIN = 0x3

with open("../config.json", "r") as f:
    config_params = json.load(f)


def generate_server_name(name):
    name_to_bytes = name.encode('utf-8')
    packed_name = struct.pack('32s', name_to_bytes)
    return packed_name


def get_offer_msg(server_port, server_name):
    packet_msg = struct.pack('! I B H 32s',
                             int(config_params["magic_cookie"], 16),
                             int(config_params["msg_type_offer"], 16),
                             server_port,
                             server_name)
    return packet_msg


def send_card(magic_cookie, msg_type, card, result, sock):
    card_packet = struct.pack(
        '!IBBHB',
        magic_cookie,
        msg_type,
        result,
        card.rank,
        card.shape
    )
    sock.sendall(card_packet)

def game_result_to_code(result):
    if result == "win":
        return RESULT_WIN
    if result == "loss":
        return RESULT_LOSS
    if result == "tie":
        return RESULT_TIE
    return ROUND_NOT_OVER


def run_server_offer(name, tcp_port):
    server_name = generate_server_name(name)
    offer_msg = get_offer_msg(tcp_port, server_name)

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        udp_sock.sendto(offer_msg, ('255.255.255.255', 13122))
        udp_sock.sendto(offer_msg, ('192.168.1.255', 13122))
        time.sleep(1)


def run_server_request(socket):
    player_semaphore = threading.Semaphore(8)

    def handle_client(client_sock, client_addr):
        print("handle client")
        player_semaphore.acquire()
        print("Player joined:", client_addr)

        try:
            data = client_sock.recv(1024)
            if not data:
                return

            magic, msg_type, rounds, name = struct.unpack('! I B B 32s', data)
            name = name.rstrip(b'\x00').decode()

            print("Received from client:", magic, msg_type, rounds, name)

            # start game
            for r in range(rounds):
                print(f"Starting round {r + 1}")
                game = Game()
                game.start()

                # first payload:
                send_card(int(config_params["magic_cookie"], 16), int(config_params["msg_type_payload"], 16), game.player_hand.cards[0], ROUND_NOT_OVER, client_sock)
                send_card(int(config_params["magic_cookie"], 16), int(config_params["msg_type_payload"], 16), game.player_hand.cards[1], ROUND_NOT_OVER, client_sock)
                send_card(int(config_params["magic_cookie"], 16), int(config_params["msg_type_payload"], 16), game.dealer_hand.cards[0], ROUND_NOT_OVER, client_sock)

                # waiting to client to determine hit/stand
                while True:
                    decision = client_sock.recv(1024)
                    if not decision:
                        print("Client disconnected during round")
                        return

                    decision = decision.strip().decode()
                    print("Client decision:", decision)

                    if decision == "Hit":
                        card = game.player_hit()

                        if game.player_hand.is_bust():
                            send_card(
                                int(config_params["magic_cookie"], 16),
                                int(config_params["msg_type_payload"], 16),
                                card,
                                RESULT_LOSS,
                                client_sock
                            )
                            break

                        send_card(
                            int(config_params["magic_cookie"], 16),
                            int(config_params["msg_type_payload"], 16),
                            card,
                            ROUND_NOT_OVER,
                            client_sock
                        )

                    elif decision == "Stand":

                        game.player_stand()
                        for card in game.dealer_hand.cards[1:-1]:
                            send_card(
                                int(config_params["magic_cookie"], 16),
                                int(config_params["msg_type_payload"], 16),
                                card,
                                ROUND_NOT_OVER,
                                client_sock
                            )

                        result_str = game.result()
                        result_code = game_result_to_code(result_str)

                        send_card(
                            int(config_params["magic_cookie"], 16),
                            int(config_params["msg_type_payload"], 16),
                            game.dealer_hand.cards[-1],
                            result_code,
                            client_sock
                        )

                        break

                    else:
                        print("Invalid decision received:", decision)

        finally:
            player_semaphore.release()
            client_sock.close()
            print("Player left:", client_addr)

    # CREATE SERVER SOCKET ONCE

    socket.listen()

    print(f"TCP listening on port {socket.getsockname()[1]}")

    while True:
        client_sock, client_addr = socket.accept()
        print("client accepted ", client_addr)

        threading.Thread(
            target=handle_client,
            args=(client_sock, client_addr),
            daemon=True
        ).start()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("Invalid Arguments")

    name = sys.argv[1]

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind(('', 0))
    tcp_sock.listen()

    tcp_port = tcp_sock.getsockname()[1]
    print(f"TCP listening on port {tcp_port}")

    # TCP accept loop
    threading.Thread(
        target=run_server_request,
        args=(tcp_sock,),
        daemon=True
    ).start()

    # UDP broadcaster
    run_server_offer(name, tcp_port)
