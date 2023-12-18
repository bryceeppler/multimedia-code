class AudioStream:
    def __init__(self, filename):
        """
        Initialize the audio stream with the given filename.
        """
        self.filename = filename
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError("Could not open file")
        self.packetNum = 0

    def nextPacket(self):
        """
        Get the next audio packet.
        """
        packet_size = 1024
        data = self.file.read(packet_size)
        if data:
            self.packetNum += 1
        return data

    def packetNumber(self):
        """
        Get the current packet number.
        """
        return self.packetNum