from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet.protocol import DatagramProtocol
from message import RTCMessage, RTCData, Candidate
from log import Logger
import random, string
from ccnxsocket import CcnxSocket, PeetsClosure
from pyccn import Name, Interest
import pyccn
from apscheduler.scheduler import Scheduler
import operator

class PeetsServerProtocol(WebSocketServerProtocol):
  ''' a protocol class that interacts with the webrtc.io.js front end to mainly do two things:
  facilitate the establishment of webrtc peer connection and less importently, relay the text
  messages
  '''

  __logger = Logger.get_logger('PeetsServerProtocol')
  (Stopped, Probing, Streaming) = range(3)

  # a decorator method for logging. using decorator just for fun
  def logging(fn):
    def wrapper(*args, **kwargs):
      PeetsServerProtocol.__logger.debug("%s(%s, %s)", fn.__name__, args, kwargs)
      # do the actual work
      fn(*args, **kwargs) 

    return wrapper


  def __init__(self, *args, **kwargs):
    #WebSocketServerProtocol.__init__(self, *args, **kwargs)
    lst = map(lambda x: random.choice(string.ascii_letters + string.digits), range(16))
    self.id = ''.join(lst)
    self.media_sink_ports = {}
    self.media_source_port = None
    self.media_source_sdp = None
    self.ip = None
    self.local_seq = 0
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = PeetsServerProtocol.Stopped
    self.timeouts = 0

  def reset(self):
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = PeetsServerProtocol.Stopped
    self.timeouts = 0
    
  def onOpen(self):
    pass

  #@logging
  def onMessage(self, msg, binary):
    #print "Message is", msg
    self.factory.process(self, msg)

  def onClose(self, wasClean, code, reason):
    self.factory.unregister(self)

  def connectionLost(self, reason):
    WebSocketServerProtocol.connectionLost(self, reason)
    self.factory.unregister(self)

  #@logging
  def sendMessage(self, msg, binary = False):
    WebSocketServerProtocol.sendMessage(self, msg, binary)


class PeetsServerFactory(WebSocketServerFactory):
  ''' a factory class that does housing keeping job
  '''

  __logger = Logger.get_logger('PeetsServerFactory')
  
  def __init__(self, url = None, protocols = [], debug = False, debugCodePaths = False):
    # super can only work with new style classes which inherits from object
    # apparently WebSocketServerFactory is old style class
    WebSocketServerFactory.__init__(self, url = url, protocols = protocols, debug = debug, debugCodePaths = debugCodePaths)
    self.handlers = {'join_room' : self.handle_join, 'send_ice_candidate' : self.handle_ice_candidate, 'send_offer' : self.handle_offer, 'send_answer' : self.handle_answer, 'chat_msg': self.handle_chat}
    self.clients = []
    self.listen_port = 9003

  def unregister(self, client):
    if client in self.clients:
      self.handle_leave(client)
      PeetsServerFactory.__logger.info("unregister client %s", client.id)
      self.clients.remove(client)


  def process(self, client, msg):
    rtcMsg = RTCMessage.from_string(msg)
    handler = self.handlers.get(rtcMsg.eventName)
    if handler is not None:
      handler(client, rtcMsg.data)
    else:
      PeetsServerFactory.__logger.error("Unknown event name: " + rtcMsg.eventName)

  def handle_join(self, client, data):
    if not client in self.clients:
      PeetsServerFactory.__logger.info('register client %s', client.id)

      d = RTCData(socketId = client.id)
      msg = RTCMessage('new_peer_connected', d)
      self.broadcast(client, msg)

      ids = map(lambda c: c.id, self.clients)

      d = RTCData(connections = ids)
      msg = RTCMessage('get_peers', d)
      client.sendMessage(msg.to_string())

      self.clients.append(client)
    else:
      PeetsServerFactory.__logger.info("Redundant join message from: %s" + client.id)

  def handle_leave(self, client):
    data = RTCData(socketId = client.id)
    msg = RTCMessage('remove_peer_connected', data)
    self.broadcast(client, msg)

  def handle_ice_candidate(self, client, data):
    candidate = Candidate.from_string(data.candidate)
    if client.media_sink_ports.get(data.socketId) is None:
      client.media_sink_ports[data.socketId] = int(candidate.port)
      if client.media_source_port is None:
        client.media_source_port = int(candidate.port)
      if client.ip is None:
        client.ip = candidate.ip
      
      candidate = Candidate(('127.0.0.1', str(self.listen_port)))
      d = RTCData(candidate = str(candidate), socketId = client.id)
      msg = RTCMessage('receive_ice_candidate', d)
    
      for c in self.clients:
        if c.id == data.socketId:
          c.sendMessage(msg.to_string())

  def handle_offer(self, client, data):
    if client.media_source_sdp is None:
      client.media_source_sdp = data.sdp

    d = RTCData(sdp = client.media_source_sdp, socketId = client.id)
    msg = RTCMessage('receive_offer', d)
    #self.broadcast(client, msg)
    for c in self.clients:
      if c.id == data.socketId:
        c.sendMessage(msg.to_string())

  def handle_answer(self, client, data):
    if client.media_source_sdp is None:
      client.media_source_sdp = data.sdp
    d = RTCData(sdp = client.media_source_sdp, socketId = client.id)
    msg = RTCMessage('receive_answer', d)
    #self.broadcast(client, msg)
    for c in self.clients:
      if c.id == data.socketId:
        c.sendMessage(msg.to_string())

  def handle_chat(self, client, data):
    msg = RTCMessage('receive_chat_msg', data)
    self.broadcast(client, msg)

  def broadcast(self, client, msg):
    str_msg = msg.to_string()
    for c in self.clients:
      if c is not client:
        c.sendMessage(str_msg)


class PeetsTranslator(DatagramProtocol):
  ''' A translator protocol to relay local udp traffic to NDN and remote NDN traffic to local udp
  This class also implements the strategy for fetching remote data.
  If the remote seq is unknown, use a short prefix without seq to probe;
  otherwise use a naive leaking-bucket like method to fetch the remote data
  '''
  def __init__(self, factory, pipe_size):
    self.factory = factory
    self.pipe_size = pipe_size
    self.factory = factory
    # here we use two sockets, because the pending interests sent by a socket can not be satisified
    # by the content published later by the same socket
    self.ccnx_int_socket = CcnxSocket()
    self.ccnx_int_socket.start()
    self.ccnx_con_socket = CcnxSocket()
    self.ccnx_con_socket.start()
    self.stream_closure = PeetsClosure(self.stream_callback, self.stream_timeout_callback)
    self.probe_closure = PeetsClosure(self.probe_callback, self.probe_timeout_callback)
    self.scheduler = Scheduler()
    self.scheduler.start()
    self.scheduler.add_interval_job(self.fetch_media, seconds = 0.01)
    
  def datagramReceived(self, data, (host, port)):
    clients = self.factory.clients
    for c in clients:
      # only publishes one copy of the video
      if c.media_source_port == port:
        name = '/local/test/' + c.id + '/' + str(c.local_seq)
        c.local_seq += 1
        self.ccnx_con_socket.publish_content(name, data)

      if port in c.media_sink_ports.values():
        print 'udp received', c.id, host, port


  def stream_callback(self, interest, data):
    name = data.name
    content = data.content
    cid, seq = str(name).split('/')[-2:]
    clients = self.factory.clients
    for c in clients:
      if c.id != cid and cid in c.media_sink_ports:
        self.transport.write(content, (c.ip, c.media_sink_ports[cid]))
      else:
        c.fetched_seq = int(seq)
        c.timeouts = 0

  def probe_callback(self, interest, data):
    name = data.name
    content = data.content
    cid, seq = str(name).split('/')[-2:]
    #self.stream_callback(interest, data)
    for c in self.factory.clients:
      if c.id == cid:
        c.requested_seq = int(seq)
        c.fetched_seq = int(seq)
        c.timeouts = 0
        c.streaming_state = PeetsServerProtocol.Streaming

  def stream_timeout_callback(self, interest):
    # do not reexpress for non-probing interest
    name = interest.name
    cid = str(name).split('/')[-2]
    for c in self.factory.clients:
      if c.id == cid:
        c.timeouts += 1
        if c.timeouts >= self.pipe_size:
          #print self.pipe_size, 'consecutive timeouts', interest.name
          c.reset()
          
    return pyccn.RESULT_OK

  def probe_timeout_callback(self, interest):
    return pyccn.RESULT_REEXPRESS
    
  def fetch_media(self):
    clients = self.factory.clients
    if len(clients) < 2:
      pass
    
    for c in clients:
      if c.streaming_state == PeetsServerProtocol.Stopped:

        name = '/local/test/' + c.id

        template = Interest(childSelector = 1)
        self.ccnx_int_socket.send_interest(Name(name), self.probe_closure, template)
        c.streaming_state = PeetsServerProtocol.Probing
        
      elif c.streaming_state == PeetsServerProtocol.Streaming and c.requested_seq - c.fetched_seq < self.pipe_size:
          name = '/local/test/' + c.id + '/' + str(c.requested_seq + 1)
          c.requested_seq += 1
          #print 'streaming: ', name
          self.ccnx_int_socket.send_interest(Name(name), self.stream_closure)
          if c.requested_seq % 100 == 0:
            pass
            #print map(lambda c: c.id, clients)
            print map(lambda c: c.media_sink_ports, clients)
      else:
        #print 'c.streaming_state', c.streaming_state
        pass

if __name__ == '__main__':
  peets_factory = PeetsServerFactory("ws://localhost:8000")
  peets_factory.protocol = PeetsServerProtocol
  PeetsTranslator(peets_factory, 100)
  from time import sleep
  sleep(2)       
    
    

