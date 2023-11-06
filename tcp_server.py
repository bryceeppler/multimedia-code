import socket
import threading
import time

songs = [ "titanium.mp3", "the-beat-of-nature.mp3", "baby-mandala.mp3"]

server_song_index = 0
server_song_position = 0

def select_next_song():
    global server_song_index, server_song_position
    server_song_index = (server_song_index + 1) % len(songs)  # loop back to the first song after the last
    server_song_position = 0  # reset song position
    print(f"Playing {songs[server_song_index]}")

def handle_client(conn, addr, clients):

    # New client connects
    global state
    global server_song_position

    try:
        print(f"New client on {addr}")
        clients.append(conn)
        print(f"Predicted song position is {server_song_position}")

        conn.sendall(f"{state}|{songs[server_song_index]}|{server_song_position}".encode())  # send initial state

        while True:
            # Receive commands
            command_data = conn.recv(1024).decode()
            command_parts = command_data.split('|')
            command = command_parts[0]
            command_song_position = int(command_parts[1]) if len(command_parts) > 1 else None
            server_song_position = command_song_position
            print(f"sending song position {server_song_position}")
            if command == 'toggle':
                state = 'playing' if state == 'paused' else 'paused'
                print(f"State changed to {state} at position {command_song_position}")
                for client in clients:
                    client.sendall(f"{state}|{songs[server_song_index]}|{command_song_position}".encode())
            elif command == 'next':
                select_next_song()
                for client in clients:
                    client.sendall(f"{state}|{songs[server_song_index]}|{command_song_position}".encode())
            else:
                print(f"Unknown command: {command}")
                raise Exception(f"Unknown command: {command}")
    except Exception as e:
        print(f"Client {addr} disconnected: {e}")
    finally:
        clients.remove(conn)
        conn.close()
        print("Connection closed.")


# Server setup
HOST = '127.0.0.1'
PORT = 65432

state = 'paused'  # Current state: playing/paused
clients = []


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        client_thread = threading.Thread(target=handle_client, args=(conn, addr, clients))
        client_thread.daemon = True
        client_thread.start()
