#!/usr/bin/python
'''
  @author: Deepanshu Mehndiratta
  @email: contact@deepanshumehndiratta.com
  @title: FaekCast
  @description: Cast audio out of linux box (including seperate applications) from Chromium browser extension using MPEG HTTP Stream
'''

import numpy
import jack
import time
import sys
import io
import struct
import warnings
import scipy.io.wavfile
from numpy.compat import asbytes
from Queue import Queue
from threading import Thread
from numpy import array, getbuffer, frombuffer
from pydub import AudioSegment
from socket import *

jack.attach("captest")

print jack.get_ports()

jack.register_port("in_1", jack.IsInput)
jack.register_port("in_2", jack.IsInput)
jack.register_port("out_1", jack.IsOutput)
jack.register_port("out_2", jack.IsOutput)

jack.activate()

print jack.get_ports()

jack.connect("Banshee:out_audiosink-actual-sink-jackaudio_1", "captest:in_1")
jack.connect("Banshee:out_audiosink-actual-sink-jackaudio_2", "captest:in_2")
jack.connect("captest:out_1", "system:playback_1")
jack.connect("captest:out_2", "system:playback_2")

print jack.get_connections("captest:in_1")

class ClientHandler(Thread):

  def __init__(self, queue, socket):
    Thread.__init__(self)
    self.__queue = queue
    self.__socket = socket
    self.BUFFER = None

  def run(self):
    self.__socket.sendall('HTTP/1.0 200 OK\r\n')
    self.__socket.sendall('Content-Type: audio/mpeg\n\n')
    while True:
      try:
        if not self.BUFFER:
          self.BUFFER = self.__queue.get()
        else:
          self.BUFFER += self.__queue.get()
        if len(self.BUFFER) >= 8192:
          self.__socket.send(self.BUFFER)
          self.BUFFER = None
      except Exception,e:
        print str(e)
        pass


class HTTPStreamingServer:
  queues = []

  def __init__(self, host, port):
    self.__host = host
    self.__port = port
    self.__socket = socket(AF_INET, SOCK_STREAM)
    self.__socket.bind((host, port))
    self.__socket.listen(5)

  def listen(self):
    while True:
      (clientsocket, address) = self.__socket.accept()
      q = Queue()
      self.queues.append(q)
      ClientHandler(q, clientsocket).start()

# Write a wave-file
# sample rate, data
def write(fid, rate, data):
  """
  Write a numpy array as a WAV file

  Parameters
  ----------
  filename : file
    The name of the file to write (will be over-written).
  rate : int
    The sample rate (in samples/sec).
  data : ndarray
    A 1-D or 2-D numpy array of integer data-type.

  Notes
  -----
  * Writes a simple uncompressed WAV file.
  * The bits-per-sample will be determined by the data-type.
  * To write multiple-channels, use a 2-D array of shape
    (Nsamples, Nchannels).

  """
  # fid = open(filename, 'wb')
  fid.write(asbytes('RIFF'))
  fid.write(asbytes('\x00\x00\x00\x00'))
  fid.write(asbytes('WAVE'))
  # fmt chunk
  fid.write(asbytes('fmt '))
  if data.ndim == 1:
    noc = 1
  else:
    noc = data.shape[1]
  bits = data.dtype.itemsize * 8
  sbytes = rate*(bits // 8)*noc
  ba = noc * (bits // 8)
  fid.write(struct.pack('<ihHIIHH', 16, 1, noc, rate, sbytes, ba, bits))
  # data chunk
  fid.write(asbytes('data'))
  fid.write(struct.pack('<i', data.nbytes))
  import sys
  if data.dtype.byteorder == '>' or (data.dtype.byteorder == '=' and sys.byteorder == 'big'):
    data = data.byteswap()
  fid.write(data.tostring())
  # data.tofile(fid)
  # Determine file size and place it in correct
  #  position at start of the file.
  size = fid.tell()
  fid.seek(4)
  fid.write(struct.pack('<i', size-8))

def process_stream(queue, app):
  Sr = float(jack.get_sample_rate())
  while True:
    try:
      wav, mp3 = io.BytesIO(), io.BytesIO()
      write(wav, int(Sr), queue.get())
      AudioSegment.from_wav(wav).export(mp3, format="mp3", bitrate="64k")
      wav.close()
      while True:
        d = mp3.read(8192)
        if not d:
          break
        for q in app.queues:
          q.put(d)
      mp3.close()
    except Exception,e:
      print str(e)
      pass

def input_loop(queue):

  N = jack.get_buffer_size()
  Sr = float(jack.get_sample_rate())

  while True:

    capture = numpy.zeros((2,int(Sr)), 'f')
    input = numpy.zeros((2,N), 'f')
    output = numpy.zeros((2,N), 'f')

    i = 0
    while i < capture.shape[1] - N:
      try:
        jack.process(output, capture[:,i:i+N])
        i += N
      except jack.InputSyncError, e:
        print str(e)
        pass
      except jack.OutputSyncError,E:
        print str(E)
        pass
    data = numpy.array((2**15-1)*capture.transpose(),dtype="int16")
    queue.put(data)      
  print 'Lost input stream'
  sys.exit()

if __name__ == '__main__':

  app = HTTPStreamingServer("", 1337)
  q = Queue()

  print 'Launching input stream thread.'
  t1 = Thread(target=input_loop, args=[q])
  t1.setDaemon(True)
  t1.start()

  print 'Launching MP3 encoding thread.'
  t2 = Thread(target=process_stream, args=[q, app])
  t2.setDaemon(True)
  t2.start()

  try:
    print 'Starting HTTP Streaming server.'
    app.listen()
  except KeyboardInterrupt:
    print "Shutdown HTTP Streaming server."