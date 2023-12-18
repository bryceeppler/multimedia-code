import soundfile as sf
import sounddevice as sd
import numpy as np

def play_opus_file(file_path, chunk_size=1024):
    # open with soundfile
    with sf.SoundFile(file_path) as f:
        # Get file samplerate and channels
        samplerate = f.samplerate
        channels = f.channels

        print('samplerate: ', samplerate)
        print('channels: ', channels)

        # init sounddevice stream
        with sd.OutputStream(samplerate=samplerate, channels=channels) as stream:
            while True:
                data = f.read(chunk_size)
                if not data.any():
                    break
                # Convert data to 'float32', sounddevice only accepts 'float32'
                data = np.array(data, dtype=np.float32)
                stream.write(data)

play_opus_file('sample4.opus')

