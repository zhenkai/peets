from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet.protocol import DatagramProtocol
from message import RTCMessage, RTCData, Candidate
from log import Logger
import random, string

class PeetsServerProtocol(WebSocketServerProtocol):
  ''' a protocol class that interacts with the webrtc.io.js front end to mainly do two things:
  facilitate the establishment of webrtc peer connection and less importently, relay the text
  messages
  '''

  __logger = Logger.get_logger('PeetsServerProtocol')

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
    self.media_port = None
    self.ip = None
  
  def onOpen(self):
    pass

  @logging
  def onMessage(self, msg, binary):
    print "Message is", msg
    self.factory.process(self, msg)

  def onClose(self, wasClean, code, reason):
    self.factory.unregister(self)

  def connectionLost(self, reason):
    WebSocketServerProtocol.connectionLost(self, reason)
    self.factory.unregister(self)

  @logging
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
    #d = RTCData(label = data.label, candidate = data.candidate, socketId = client.id)
    #msg = RTCMessage('receive_ice_candidate', d)
    candidate = Candidate.from_string(data.candidate)
    if client.media_port is None:
      client.media_port = int(candidate.port)
      client.ip = candidate.ip
      
    candidate = Candidate(('127.0.0.1', str(self.listen_port)))
    d = RTCData(label = data.label, candidate = str(candidate), socketId = client.id)
    msg = RTCMessage('receive_ice_candidate', d)
    
    self.broadcast(client, msg)

  def handle_offer(self, client, data):
    d = RTCData(sdp = data.sdp, socketId = client.id)
    msg = RTCMessage('receive_offer', d)
    self.broadcast(client, msg)

  def handle_answer(self, client, data):
    d = RTCData(sdp = data.sdp, socketId = client.id)
    msg = RTCMessage('receive_answer', d)
    self.broadcast(client, msg)

  def handle_chat(self, client, data):
    msg = RTCMessage('receive_chat_msg', data)
    self.broadcast(client, msg)

  def broadcast(self, client, msg):
    str_msg = msg.to_string()
    print "Broadcasting to ", self.clients
    for c in self.clients:
      if c is not client:
        c.sendMessage(str_msg)


class PeetsUDP(DatagramProtocol):
  ''' A udp protocol to relay local udp traffic to NDN and remote NDN traffic to local udp
  '''
  def __init__(self, factory):
    self.factory = factory
    
  def datagramReceived(self, data, (host, port)):
    print 'data received: ', host, port
    clients = self.factory.clients
    for c in clients:
      if c.media_port != port:
        self.transport.write(data, (c.ip, c.media_port))
        print 'sent data to: ', c.ip, c.media_port
    

