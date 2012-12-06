import json
from log import Logger
from user import User

class PeetsMessage(object):
  ''' a message class that carries prescence and NDN related info of a participant
  '''
  Join, Hello, Leave, Chat = range(4)  

  def __init__(self, msg_type, user, extra = None, *args, **kwargs):
    super(PeetsMessage, self).__init__()
    self.msg_type = msg_type
    self.user =  user
    self.extra = extra

  def __str__(self):
    class PeetsMessageEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
    
    return json.dumps(self, cls = PeetsMessageEncoder)

  @classmethod
  def from_string(self, str_msg):
    dct = json.loads(str_msg)
    return PeetsMessage(dct.get('msg_type'), User(**dct.get('user')), dct.get('extra'))

class RTCMessage(object):
  ''' a class that interacts with webrtc.io.js using their defined message
  '''
  def __init__(self, eventName, data, *args, **kwargs):
    super(RTCMessage, self).__init__()
    self.eventName = eventName
    self.data = data

  def __str__(self):
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
    if kwargs.get('sdp') is not None:
      self.sdp = kwargs.get('sdp')
    if kwargs.get('socketId') is not None:
      self.socketId = kwargs.get('socketId')
    # we store the stringified version of candidate in data, as the stringify method for Candidate is a little different
    if kwargs.get('candidate') is not None:
      self.candidate = kwargs.get('candidate')
    if kwargs.get('room') is not None:
      self.room = kwargs.get('room')
    if kwargs.get('connections') is not None:
      self.connections = kwargs.get('connections')
    if kwargs.get('color') is not None:
      self.color = kwargs.get('color')
    if kwargs.get('messages') is not None:
      self.messages = kwargs.get('messages')

  def __str__(self):
    class RTCDataEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
      
    return json.dumps(self, cls = RTCDataEncoder)

  @classmethod
  def from_string(self, str_msg):
    def as_message(dct):
      return RTCData(sdp = dct.get('sdp'), socketId = dct.get('socketId'), candidate = dct.get('candidate'), room = dct.get('room'), connections = dct.get('connections'))

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
    c = Candidate.from_string(str(Candidate(('127.0.0.1', '62323'))))
    print c
    
    d = RTCData(candidate = str(c))
    print d

    dd = RTCData.from_string(str(d))
    print dd

    empty_room = RTCData(messages = "hello, world", room = "")
    print empty_room

    m = RTCMessage('new candidate', d)
    print m

    mm = RTCMessage.from_string(str(m))
    print mm

    d = RTCData(connections = [])
    print d

    str_msg = '{"socketId":"ufGE27a4p8xnXAEx","sdp":"v=0\r\no=- 1231441458 1 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\na=group:BUNDLE audio video\r\nm=audio 1 RTP/SAVPF 103 104 0 8 106 105 13 126\r\nc=IN IP4 0.0.0.0\r\na=rtcp:1 IN IP4 0.0.0.0\r\na=ice-ufrag:4JJeOjkTn3Pdi1JT\r\na=ice-pwd:R2W7uiQVJR+cFwoIEnpXg4FN\r\na=sendrecv\r\na=mid:audio\r\na=rtcp-mux\r\na=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:9Qx2eyCceVteTJSp+gN77PMe7Wdv0jLkX0rOD9ya\r\na=rtpmap:103 ISAC/16000\r\na=rtpmap:104 ISAC/32000\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:8 PCMA/8000\r\na=rtpmap:106 CN/32000\r\na=rtpmap:105 CN/16000\r\na=rtpmap:13 CN/8000\r\na=rtpmap:126 telephone-event/8000\r\na=ssrc:1849461185 cname:K3SOgLblDl9rwkwG\r\na=ssrc:1849461185 mslabel:IW3y3wkSByKDZXcf8FzgXk7a5wPfmYf3KxXM\r\na=ssrc:1849461185 label:IW3y3wkSByKDZXcf8FzgXk7a5wPfmYf3KxXM00\r\nm=video 1 RTP/SAVPF 100 101 102\r\nc=IN IP4 0.0.0.0\r\na=rtcp:1 IN IP4 0.0.0.0\r\na=ice-ufrag:4JJeOjkTn3Pdi1JT\r\na=ice-pwd:R2W7uiQVJR+cFwoIEnpXg4FN\r\na=sendrecv\r\na=mid:video\r\na=rtcp-mux\r\na=crypto:1 AES_CM_128_HMAC_SHA1_80 inline:9Qx2eyCceVteTJSp+gN77PMe7Wdv0jLkX0rOD9ya\r\na=rtpmap:100 VP8/90000\r\na=rtpmap:101 red/90000\r\na=rtpmap:102 ulpfec/90000\r\na=ssrc:2046667548 cname:K3SOgLblDl9rwkwG\r\na=ssrc:2046667548 mslabel:IW3y3wkSByKDZXcf8FzgXk7a5wPfmYf3KxXM\r\na=ssrc:2046667548 label:IW3y3wkSByKDZXcf8FzgXk7a5wPfmYf3KxXM10\r\n"}'.replace('\r\n', '\\r\\n')

    mm = RTCData.from_string(str_msg)
    print mm

    peets_msg = PeetsMessage(PeetsMessage.Join, User('obama', '/whitehouse', '/whitehouse/restroom', 'maobama'))
    
    print peets_msg

    pmf = PeetsMessage.from_string(str(peets_msg))
    print pmf
