import struct
import sys
import socket
import json
import time

with open("../config.json", "r") as f:
    config_params = json.load(f)

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
        return sock


    while True:
        print("got here")
        data, addr = sock.recvfrom(39)
        print(f"Received {len(data)} bytes from {addr}")

        magic_cookie, msg_type, server_port, server_name = struct.unpack('! I B H 32s', data)
        server_name = server_name.rstrip(b'\x00').decode('utf-8')
        #server_name = name.encode('utf-8').rstrip('\x00')
        print(f"Server: {server_name}, TCP port: {server_port}")
        if not check_cookie(magic_cookie):
            print(magic_cookie)
            continue
        game_socket = connect_to_server(addr[0], server_port, magic_cookie)



        #play game logic
        print("send request")
        while True:
            continue



if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise "Invalid Arguments"
    name = sys.argv[1]
    run_server(name)
