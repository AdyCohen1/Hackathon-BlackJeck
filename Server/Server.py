import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socket import socket
import struct
from scapy.all import *
from scapy.layers.inet import UDP, IP
import threading


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
            client_sock.sendall(b"Welcome! Game starting.\n")

            while True:
                data = client_sock.recv(1024)
                magic, msg_type, rounds, name = struct.unpack('! I B B 32s', data)
                name = name.rstrip(b'\x00').decode()

                print("Received from client:", magic, msg_type, rounds, name)
                if not data:
                    break

                client_sock.sendall(b"ACK\n")

        finally:
            player_semaphore.release()
            client_sock.close()
            print("Player left:", client_addr)

    # 🔹 CREATE SERVER SOCKET ONCE

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



