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

