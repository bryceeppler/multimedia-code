import pyogg
import sounddevice as sd
import time

def play_opus_file(file_path):
    # Load the Opus file
    opus_file = pyogg.OpusFile(file_path)

    # Convert to a NumPy array for playback
    audio_data = opus_file.as_array()

    # Play the audio
    sd.play(audio_data, samplerate=opus_file.frequency)

    # Wait for the audio to finish playing
    duration = len(audio_data) / opus_file.frequency
    time.sleep(duration)

# Path to your Opus file
file_path = 'sample4.opus'

# Play the file
play_opus_file(file_path)
