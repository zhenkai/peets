from autobahn.websocket import WebSocketServerProtocol, WebSocketServerFactory
from twisted.internet.protocol import DatagramProtocol
from message import RTCMessage, RTCData, Candidate, PeetsMessage
from user import User, RemoteUser
from roster import Roster
from log import Logger
import random, string
from ccnxsocket import CcnxSocket, PeetsClosure
from pyccn import Interest, Closure
import pyccn
from apscheduler.scheduler import Scheduler
import operator
from time import sleep
from pktparser import StunPacket, RtpPacket, RtcpPacket
from softstate import StateObject

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
    self.local_user = User(self.id, '/local/test', self.id)
    self.media_sink_ports = {}
    self.media_source_port = None
    self.media_source_sdp = None
    self.ip = None
    self.local_seq = 0
    self.ctrl_seqs = {}
    self.remote_cids = {}

    
  def onOpen(self):
    pass

  #@logging
  def onMessage(self, msg, binary):
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
  
  def __init__(self, udp_port, url = None, protocols = [], debug = False, debugCodePaths = False):
    # super can only work with new style classes which inherits from object
    # apparently WebSocketServerFactory is old style class
    WebSocketServerFactory.__init__(self, url = url, protocols = protocols, debug = debug, debugCodePaths = debugCodePaths)
    self.handlers = {'join_room' : self.handle_join, 'send_ice_candidate' : self.handle_ice_candidate, 'send_offer' : self.handle_offer, 'media_ready' : self.handle_media_ready, 'chat_msg': self.handle_chat}
    # keep the list of local clients, first, we deal with the case where there is only one local client
    self.client = None
    # keep the list of remote users
    self.roster = None
    self.listen_port = udp_port
    self.__class__.__logger.debug('UDP-PORT=%s', str(udp_port))
    self.ccnx_socket = CcnxSocket()
    self.ccnx_socket.start()
    self.local_status_callback = lambda status: 0

  def set_local_status_callback(self, callback):
    self.local_status_callback = callback

  def sdp_callback(self, interest, data):
    content = data.content
    offer_msg = RTCMessage.from_string(content)
    d = RTCData(socketId = self.client.id, sdp = offer_msg.data.sdp)
    # this is the answer to the local user
    answer_msg = RTCMessage('receive_answer', offer_msg.data)
    self.client.sendMessage(str(answer_msg))
    remote_user = self.roster[offer_msg.data.socketId]
    remote_user.set_sdp_sent()
    # we received ice candidate before sending answer
    if remote_user.ice_candidate_msg is not None:
      self.client.sendMessage(str(remote_user.ice_candidate_msg))

  def peets_msg_callback(self, peets_msg):
    remote_user = RemoteUser(peets_msg.user)
    if peets_msg.msg_type == PeetsMessage.Join or peets_msg.msg_type == PeetsMessage.Hello:
      if self.roster.has_key(remote_user.uid):
        self.__class__.__logger.debug("Redundant join message from %s", remote_user.get_sync_prefix())
        exit(0)
        return
      
      self.roster[remote_user.uid] = remote_user
      self.__class__.__logger.debug("Peets join message from remote user: %s", remote_user.get_sync_prefix())
      data = RTCData(socketId = remote_user.uid)
      msg = RTCMessage('new_peer_connected', data)
      self.client.sendMessage(str(msg))
      name = remote_user.get_sdp_prefix()
      
      self.ccnx_socket.send_interest(name, PeetsClosure(msg_callback = self.sdp_callback))
      

    elif peets_msg.msg_type == PeetsMessage.Leave:
      del self.roster[remote_user.uid]
      self.__class__.__logger.debug("Peets leave message from remote user: %s", remote_user.get_sync_prefix())
      data = RTCData(socketId = remote_user.uid)
      msg = RTCMessage('remove_peer_connected', data)
      self.client.sendMessage(str(msg))
    elif peets_msg.msg_type == PeetsMessage.Chat:
      data = RTCData(socketId = remote_user.uid, messages = peets_msg.extra)
      msg = RTCMessage('receive_chat_msg', data)
      self.client.sendMessage(str(msg))

  def unregister(self, client):
    if self.client is not None and client.id == self.client.id:
      self.local_status_callback('Stopped')
      self.handle_leave(client)
      PeetsServerFactory.__logger.debug("unregister client %s", client.id)
      self.client = None
      self.roster = None

  def process(self, client, msg):
    rtcMsg = RTCMessage.from_string(msg)
    handler = self.handlers.get(rtcMsg.eventName)
    if handler is not None:
      handler(client, rtcMsg.data)
    else:
      PeetsServerFactory.__logger.error("Unknown event name: " + rtcMsg.eventName)

  def handle_join(self, client, data):
    PeetsServerFactory.__logger.debug('join from client %s', client.id)

    d = RTCData(connections = [])
    msg = RTCMessage('get_peers', d)
    client.sendMessage(str(msg))

  def handle_media_ready(self, client, data):
    if self.client is None:
      PeetsServerFactory.__logger.debug('register client %s', client.id)
      self.client = client
      # announce self in NDN
      self.roster = Roster('/chatroom', self.peets_msg_callback, lambda: self.client.local_user)
      self.local_status_callback('Running')
    else:
      PeetsServerFactory.__logger.debug("Join message from: %s, but we already have a client: %s", client.id, self.client.id)

  def handle_leave(self, client):
    self.roster.leave()
    sleep(1.1)
    

  # this method is local, i.e. no leak to NDN
  def handle_ice_candidate(self, client, data):
    candidate = Candidate.from_string(data.candidate)
    if client.media_sink_ports.get(data.socketId) is None:
      port = int(candidate.port)
      client.media_sink_ports[data.socketId] = port
      client.ctrl_seqs[port] = 0
      client.remote_cids[port] = data.socketId
      if client.media_source_port is None:
        client.media_source_port = int(candidate.port)
      if client.ip is None:
        client.ip = candidate.ip
      
      candidate = Candidate(('127.0.0.1', str(self.listen_port)))
      d = RTCData(candidate = str(candidate), socketId = data.socketId)
      msg = RTCMessage('receive_ice_candidate', d)
      remote_user = self.roster[data.socketId]
      remote_user.set_ice_candidate_msg(msg)
      # sdp answer has already been sent
      if remote_user.sdp_sent:
        self.client.sendMessage(str(msg))

      
  def handle_offer(self, client, data):
    if client.media_source_sdp is None:
      client.media_source_sdp = data.sdp

    d = RTCData(sdp = client.media_source_sdp, socketId = client.id)
    msg = RTCMessage('receive_offer', d)

    name = client.local_user.get_sdp_prefix() 
    # publish sdp msg
    self.ccnx_socket.publish_content(name, str(msg))


    def publish(interest):
      self.ccnx_socket.publish_content(name, str(msg))

    self.ccnx_socket.register_prefix(name, PeetsClosure(incoming_interest_callback = publish))


  def has_local_client(self):
    return self.client is not None and self.roster is not None

  def handle_chat(self, client, data):
    msg = PeetsMessage(PeetsMessage.Chat, self.client.local_user, extra = data.messages)
    self.roster.chronos_sock.publish_string(self.client.local_user.get_sync_prefix(), self.roster.session, str(msg), StateObject.default_ttl)


class PeetsMediaTranslator(DatagramProtocol):
  ''' A translator protocol to relay local udp traffic to NDN and remote NDN traffic to local udp
  This class also implements the strategy for fetching remote data.
  If the remote seq is unknown, use a short prefix without seq to probe;
  otherwise use a naive leaking-bucket like method to fetch the remote data
  '''
  __logger = Logger.get_logger('PeetsMediaTranslator')
  def __init__(self, factory, pipe_size):
    self.factory = factory
    self.pipe_size = pipe_size
    self.factory = factory
    self.factory.set_local_status_callback(self.toggle_scheduler)
    # here we use two sockets, because the pending interests sent by a socket can not be satisified
    # by the content published later by the same socket
    self.ccnx_int_socket = CcnxSocket()
    self.ccnx_int_socket.start()
    self.ccnx_con_socket = CcnxSocket()
    self.ccnx_con_socket.start()
    self.stream_closure = PeetsClosure(msg_callback = self.stream_callback, timeout_callback = self.stream_timeout_callback)
    self.probe_closure = PeetsClosure(msg_callback = self.probe_callback, timeout_callback = self.probe_timeout_callback)
    self.ctrl_probe_closure = PeetsClosure(msg_callback = self.ctrl_probe_callback, timeout_callback = self.ctrl_probe_timeout_callback)
    self.scheduler = None
    self.peets_status = None
    
  def toggle_scheduler(self, status):
    if status == 'Running':
      self.peets_status = 'Running'
      self.scheduler = Scheduler()
      self.scheduler.start()
      self.scheduler.add_interval_job(self.fetch_media, seconds = 0.01, max_instances = 2)
    elif status == 'Stopped':
      self.peets_status = 'Stopped'
      for job in self.scheduler.get_jobs():
        self.scheduler.unschedule_job(job)
      self.scheduler.shutdown(wait = True)
      self.scheduler = None
       
  def datagramReceived(self, data, (host, port)):
    ''' 
    1. Differentiate RTP vs RTCP
    RTCP: packet type (PT) = 200 - 208
    SR (sender report)        200
    RR (receiver report)      201
    SDES (source description) 202
    BYE (goodbye)             203
    App (application-defined) 204
    other types go until      208
    RFC 5761 (implemented by WebRTC) makes sure that RTP's PT field
    plus M field (which is equal to the PT field in RTCP) would not conflict

    2. Differentiate STUN vs RTP & RTCP
    STUN: the most significant 2 bits of every STUN msg MUST be zeros (RFC 5389)
    RTP & RTCP: version bits (2 bits) value equals 2
    '''
    # mask to test most significant 2 bits
    msg = bytearray(data)
    c = self.factory.client

    if msg[0] & 0xC0 == 0 or msg[1] > 199 and msg[1] < 209:
      # Tried to fake a Stun request and response so that we don't have to
      # relay stun msgs to NDN, but failed.
      # note that we need to use the username exchanged in the sdps for stun
      # it worked for a while but magically stopped working, so now we still
      # send it over NDN
      try:
        ctrl_seq = c.ctrl_seqs[port]
        cid = c.remote_cids[port]
        name = c.local_user.get_ctrl_prefix() + '/' + cid + '/' + str(ctrl_seq)
        c.ctrl_seqs[port] = ctrl_seq + 1
        self.ccnx_con_socket.publish_content(name, data)
      except KeyError:
        pass


    elif c.media_source_port == port:
      name = c.local_user.get_media_prefix() + '/' + str(c.local_seq)
      c.local_seq += 1
      self.ccnx_con_socket.publish_content(name, data)

  def get_info_from_name(self, name):
    comps = str(name).split('/')
    cid = comps[-3]
    seq = comps[-1]
    remote_user = self.factory.roster[cid]
    return remote_user, cid, seq

  def stream_callback(self, interest, data):
    if self.peets_status != 'Running':
      return
    content = data.content
    remote_user, cid, seq = self.get_info_from_name(data.name)
    c = self.factory.client
    if cid in c.media_sink_ports:
      self.transport.write(content, (c.ip, c.media_sink_ports[cid]))
      self.__class__.__logger.debug('RTP-DATA:%s', str(data.name))

    if remote_user is not None:
      remote_user.fetched_seq = int(seq)
      remote_user.timeouts = 0

  def probe_callback(self, interest, data):
    if self.peets_status != 'Running':
      return
    content = data.content
    remote_user, cid, seq = self.get_info_from_name(data.name)
    c = self.factory.client
    if cid in c.media_sink_ports:
      self.transport.write(content, (c.ip, c.media_sink_ports[cid]))
      self.__class__.__logger.debug('RTP-DATA:%s', str(data.name))

    if remote_user is not None:
      remote_user.requested_seq = int(seq)
      remote_user.fetched_seq = int(seq)
      remote_user.timeouts = 0
      remote_user.streaming_state = RemoteUser.Streaming

  def ctrl_probe_callback(self, interest, data):
    if self.peets_status != 'Running':
      return
    # /remote-prefix/remote-nick/remote-uid/ctrl/self-uid/seq 
    comps = str(data.name).split('/')
    seq = comps[-1]
    cid = comps[-4]
    remote_user = self.factory.roster[cid]

    content = data.content
    c = self.factory.client
    if cid in c.media_sink_ports:
      self.transport.write(content, (c.ip, c.media_sink_ports[cid]))
      msg = bytearray(content)
      if msg[0] & 0xC0 == 0:
        self.__class__.__logger.debug('STUN-DATA:%s', str(data.name))
      else:
        self.__class__.__logger.debug('RTCP-DATA:%s', str(data.name))
    
    name_comps = comps[:-1]
    new_seq = int(seq) + 1
    name_comps.append(str(new_seq))
    name = '/'.join(name_comps)
    # fetch the next ctrl message
    self.ccnx_int_socket.send_interest(name, self.ctrl_probe_closure)
    self.__class__.__logger.debug('CTRL-INT:%s', str(name))
    
  def ctrl_probe_timeout_callback(self, interest):
    if self.peets_status != 'Running':
      return pyccn.RESULT_OK

    comps = str(interest.name).split('/')
    with_seq = True
    try:
      int(comps[-1])
    except ValueError:
      with_seq = False

    cid = comps[-4] if with_seq else comps[-3]
    if self.factory.roster is not None and self.factory.roster[cid] is not None:
      return pyccn.RESULT_REEXPRESS


  def stream_timeout_callback(self, interest):
    # do not reexpress for non-probing interest
    if self.peets_status != 'Running':
      return
    remote_user, cid, seq = self.get_info_from_name(interest.name)
    if remote_user is not None:
      remote_user.timeouts += 1
      if remote_user.timeouts >= self.pipe_size:
        remote_user.reset()
          
    return pyccn.RESULT_OK

  def probe_timeout_callback(self, interest):
    if self.peets_status != 'Running':
      return pyccn.RESULT_OK

    comps = str(interest.name).split('/')
    cid = comps[-2]
    if self.factory.roster is not None and self.factory.roster[cid] is not None:
      return pyccn.RESULT_REEXPRESS
    
  def fetch_media(self):
    if self.factory.has_local_client():
      for remote_user in self.factory.roster.values():
        if remote_user.streaming_state == RemoteUser.Stopped:
          name = remote_user.get_media_prefix()
          template = Interest(childSelector = 1)
          self.ccnx_int_socket.send_interest(name, self.probe_closure, template)
          self.__class__.__logger.debug('RTP-INT:%s', name)
          remote_user.streaming_state = RemoteUser.Probing

          # also fetch ctrl messages
          ctrl_name = remote_user.get_ctrl_prefix() + '/' + self.factory.client.local_user.uid
          self.ccnx_int_socket.send_interest(ctrl_name, self.ctrl_probe_closure, template)
          self.__class__.__logger.debug('CTRL-INT:%s', ctrl_name)
          
        elif remote_user.streaming_state == RemoteUser.Streaming:
          while remote_user.requested_seq - remote_user.fetched_seq < self.pipe_size:
            name = remote_user.get_media_prefix() + '/' + str(remote_user.requested_seq + 1)
            remote_user.requested_seq += 1
            self.ccnx_int_socket.send_interest(name, self.stream_closure)
            self.__class__.__logger.debug('RTP-INT:%s', name)
        else:
          pass

if __name__ == '__main__':
  peets_factory = PeetsServerFactory("ws://localhost:8000")
  peets_factory.protocol = PeetsServerProtocol
  PeetsMediaTranslator(peets_factory, 100)
  from time import sleep
  sleep(2)       
    
    

