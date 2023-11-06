import socket
import pygame
import threading

# https://www.geeksforgeeks.org/python-playing-audio-file-in-pygame/
# https://www.pygame.org/docs/ref/music.html

def get_input():
    while True:
        user_input = input("Press Enter to toggle play/pause, press N then Enter to play next song\n")

        song_position = pygame.mixer.music.get_pos()
        position_str = str(song_position)
        # Whenever a command is sent from the client, we need to send the position in the current song
        if user_input == '':
            print("Toggling play/pause")
            # Send toggle command and the position
            s.sendall(f"toggle|{position_str}".encode())
        elif user_input == 'n':
            print("Playing next song")
            # Send next command and the position
            s.sendall(f"next|{position_str}".encode())
        else:
            print("Invalid input")

pygame.mixer.init()
pygame.mixer.music.set_volume(0.7)

# Connect to server
HOST = '127.0.0.1'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    # input thread
    input_thread = threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()

    
    while True:
        # Get initial state
        data = s.recv(1024).decode()
        state, song_title, song_position = data.split('|')
        if song_position != 'None':
            song_position = float(song_position)
        else:
            song_position = 0.0 
        print(f"Current state is {state} with song {song_title} at position {song_position}")

        # get name of current song
        if pygame.mixer.music.get_busy():
            current_song = pygame.mixer.music.get_pos()
            print(f"Current song is {current_song}")
        else:
            current_song = None

        if song_title != current_song:
            print(f"Loading {song_title} into pygame")
            pygame.mixer.music.load(song_title)

        # Play or pause based on state
        if state == 'playing':
            if not pygame.mixer.music.get_busy():
                # Convert the song position from ms to seconds
                start_position = song_position / 1000.0
                # start playing the song from the given position
                pygame.mixer.music.play(-1, start_position)
            else:
                pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.pause()
