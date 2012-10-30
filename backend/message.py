import json
from log import Logger

class PeetsMessage(object):
  ''' a message class that carries prescence and NDN related info of a participant
  '''
  Join, Hello, Leave = range(3)  

  def __init__(self, msg_type, msg_from, *args, **kwargs):
    super(PeetsMessage, self).__init__()
    self.msg_type = msg_type
    self.msg_from = msg_from
    self.audio_prefix = kwargs.get('audio_prefix', None)
    self.audio_rate_hint = kwargs.get('audio_rate_hint', None)
    self.audio_seq_hint = kwargs.get('audio_seq_hint', None)

  def to_string(self):
    class PeetsMessageEncoder(json.JSONEncoder):
      def default(self, obj):
        if not isinstance(obj, PeetsMessage):
          return super(PeetsMessageEncoder, self).default(obj)
        
        if (obj.msg_type == PeetsMessage.Leave):
          return dict({'msg_type': obj.msg_type, 'msg_from': obj.msg_from})

        return obj.__dict__
    
    return json.dumps(self, cls = PeetsMessageEncoder)

  @classmethod
  def from_string(self, str_msg):

    def as_message(dct):
      if dct['msg_type'] == PeetsMessage.Leave:
        return PeetsMessage(dct['msg_type'], dct['msg_from'])
      else:
        return PeetsMessage(dct['msg_type'], dct['msg_from'], audio_prefix = dct.get('audio_prefix'), audio_rate_hint = dct.get('audio_rate_hint'), audio_seq_hint = dct.get('audio_seq_hint'))

    return json.loads(str_msg, object_hook = as_message)

class RTCMessage(object):
  ''' a class that interacts with webrtc.io.js using their defined message
  '''
  def __init__(self, eventName, data, *args, **kwargs):
    super(RTCMessage, self).__init__()
    self.eventName = eventName
    self.data = data

  def to_string(self):
    class RTCMessageEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
    return json.dumps(self, cls = RTCMessageEncoder)

  @classmethod
  def from_string(self, str_msg):
    # for some reason, the object_hook of json.loads would be caused twice if the str_msg includes nested dict
    # hence here no object_hook is used
    dct = json.loads(str_msg)
    return RTCMessage(dct.get('eventName'), RTCData(**dct.get('data')))
  
class RTCData(object):
  ''' a class that manipulates the data part of the message in webrtc.io.js
  '''
  def __init__(self, *args, **kwargs):
    super(RTCData, self).__init__()
    if kwargs.get('sdp', None):
      self.sdp == kwargs.get('sdp')
    if kwargs.get('socketId', None):
      self.socketId = kwargs.get('socketId')
    # we store the stringified version of candidate in data, as the stringify method for Candidate is a little different
    if kwargs.get('candidate', None):
      self.candidate = kwargs.get('candidate')
    if kwargs.get('room', None):
      self.room = kwargs.get('room')
    if kwargs.get('connections', None):
      self.connections = kwargs.get('connections')
    if kwargs.get('label', None):
      self.label = kwargs.get('label')

  def to_string(self):
    class RTCDataEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
      
    return json.dumps(self, cls = RTCDataEncoder)

  @classmethod
  def from_string(self, str_msg):
    def as_message(dct):
      return RTCData(sdp = dct.get('sdp'), socketId = dct.get('socketId'), candidate = dct.get('candidate'), room = dct.get('room'), connections = dct.get('connections'), label = dct.get('label'))

    return json.loads(str_msg, object_hook = as_message)

class Candidate(object):
  ''' a class that manipulates candidate msg used in webrtc
  '''
  def __init__(self,  portmap, *args, **kwargs):
    super(Candidate, self).__init__()
    self.ip, self.port = portmap

  def __str__(self):
    return 'a=candidate:4017702753 1 udp 2130714367 %s %s typ host generation 0\r\n' % (self.ip, self.port)

  @classmethod
  def from_string(self, str_msg):
    strs = str_msg.split()
    return Candidate((strs[4], strs[5]))
    
    
if __name__ == '__main__':
    msg = PeetsMessage(PeetsMessage.Hello, 'tester', audio_prefix = '/1/2/3', audio_rate_hint = 50, audio_seq_hint = 0)
    x =  msg.to_string()
    print x
    y = PeetsMessage.from_string(x)
    print y.to_string()

    msg = PeetsMessage(PeetsMessage.Leave, 'tester')
    x = msg.to_string()
    print x
    y = PeetsMessage.from_string(x)
    print y.to_string()

    c = Candidate.from_string(str(Candidate(('127.0.0.1', '62323'))))
    print c
    
    d = RTCData(label = '0', candidate = str(c))
    print d.to_string()

    dd = RTCData.from_string(d.to_string())
    print dd.to_string()

    m = RTCMessage('new candidate', d)
    print m.to_string()

    mm = RTCMessage.from_string(m.to_string())
    print mm.to_string()

    
