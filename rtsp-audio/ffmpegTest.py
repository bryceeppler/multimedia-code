import subprocess

def play_opus_file(filename):
    try:
        # Start an ffplay process to play the Opus file
        subprocess.run(["ffplay", "-nodisp", "-autoexit", filename])
    except Exception as e:
        print("Error playing file:", e)

# Replace 'sample4.opus' with the path to your Opus file
play_opus_file("sample4.opus")
