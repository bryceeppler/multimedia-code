from tkinter import *
import tkinter.messagebox as tkMessageBox
import socket, threading, sys, traceback, os
import io
import numpy as np
import sounddevice as sd
import pyogg
import subprocess

from RtpPacket import RtpPacket

BUFFER_THRESHOLD = 4096

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.packetNbr = 0
		self.audio_buffer = io.BytesIO()
		self.file_pointer = None
		self.audio_stream = None
		self.initialized_stream = False
		self.ffmpeg_process = None
		self.named_pipe_path = '/tmp/opus_fifo'  # Path for the named pipe
		self.create_named_pipe()
		self.ffplay_process = None
		self.playEvent = threading.Event()

	def create_named_pipe(self):
		"""Create a named pipe for streaming audio data."""
		try:
			os.mkfifo(self.named_pipe_path)
		except FileExistsError:
			pass  # If the pipe already exists, no need to recreate it

		
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupStream
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playStream
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseStream
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def setupStream(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	def exitClient(self):
		"""Teardown button handler."""
		if self.pipe_out:
			self.pipe_out.close()
		if self.ffmpeg_process:
			self.ffmpeg_process.terminate()
		self.sendRtspRequest(self.TEARDOWN)
		self.master.destroy()  # Close the GUI window
		os.remove(self.named_pipe_path)  # Clean up the named pipe


	def pauseStream(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
			if self.ffmpeg_process:
				self.ffmpeg_process.terminate()
				self.ffmpeg_process = None
			if self.pipe_out:
				self.pipe_out.close()
				self.pipe_out = None
			self.playEvent.clear()  # Signal to pause RTP listening thread
			self.state = self.READY
			print("Stream paused")

	def playStream(self):
		"""Play button handler."""
		if self.state in [self.READY, self.PAUSE]: 
			self.startFfmpegProcess()
			if not self.isRtpListening():
				threading.Thread(target=self.listenRtp).start()
				print("RTP listening thread restarted")
			self.playEvent.set()  # Signal to resume RTP listening thread
			self.sendRtspRequest(self.PLAY)
			self.state = self.PLAYING
			print("Stream resumed")

	def startFfmpegProcess(self):
		"""Start or restart FFmpeg process for playing audio."""
		if self.ffmpeg_process:
			self.ffmpeg_process.terminate()
		self.ffmpeg_process = subprocess.Popen(
			["ffplay", "-i", self.named_pipe_path, "-nodisp", "-autoexit"],
			stdin=subprocess.PIPE
		)
		self.pipe_out = open(self.named_pipe_path, 'wb', buffering=0)
		print("FFmpeg process started")

	def isRtpListening(self):
		"""Check if the RTP listening thread is active."""
		return not self.playEvent.is_set()
		





	def play_ffmpeg_output(self):
		"""Play audio from FFmpeg's stdout."""
		try:
			with sd.OutputStream() as stream:
				while True:
					data = self.ffmpeg_process.stdout.read(1024)
					if not data:
						break
					stream.write(np.frombuffer(data, dtype=np.float32))
		except Exception as e:
			print("play_ffmpeg_output() exception: ", str(e))


	def handleAudioData(self, data):
		"""Handle the received audio data."""
		try:
			# Continuously write Opus packets to the named pipe
			if self.pipe_out:
				self.pipe_out.write(data)
				self.pipe_out.flush()
		except Exception as e:
			print("handleAudioData() exception:", e)

 
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currPacketNumber = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currPacketNumber))
					self.handleAudioData(rtpPacket.getPayload())	

			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet(): 
					break
				
				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
			
					
	
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkMessageBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = "SETUP " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nTransport: RTP/UDP; client_port= " + str(self.rtpPort)
			# Keep track of the sent request.
			self.requestSent = self.SETUP
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = "PLAY " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId) 
			# Keep track of the sent request.
			self.requestSent = self.PLAY
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = "PAUSE " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId)
			# Keep track of the sent request.
			self.requestSent = self.PAUSE 
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			request = "TEARDOWN " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSession: " + str(self.sessionId) 
			# Keep track of the sent request.
			self.requestSent = self.TEARDOWN 
		else:
			return
		
		# Send the RTSP request using rtspSocket.
		self.rtspSocket.send(request.encode("utf-8"))
		print('\nData sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.SETUP:
						# Update RTSP state.
						self.state = self.READY
						# Open RTP port.
						self.openRtpPort() 
					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT 
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
		
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		
		try:
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind(('', self.rtpPort))
		except:
			tkMessageBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseStream()
		if tkMessageBox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playStream()
