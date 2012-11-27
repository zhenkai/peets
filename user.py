from softstate import StateObject
import json

class User(object):
  ''' Store the common information of a user '''
  Available, Unavailable = range(2)

  def __init__(self, nick, prefix, uid, *args, **kwargs):
    ''' somehow, this must also calls super in order for all 
        base classes to be initialized when the subclass calls
        its super init function

        The prefix here is the identity prefix for a user used
        in the chronos sync tree. It's not exactly the same as the
        media prefix, but may be the prefix of the media prefix
    '''
    super(User, self).__init__()
    self.nick = nick
    self.prefix = prefix
    self.uid = uid


  def get_nick(self):
    return self.nick

  def get_media_prefix(self):
    return self.prefix + '/' + self.nick + '/' + self.uid + '/media'

  def get_stun_prefix(self):
    return self.prefix + '/' + self.nick + '/' + self.uid + '/stun'

  def get_sdp_prefix(self):
    return self.prefix + '/' + self.nick + '/' + self.uid + '/sdp'

  def get_sync_prefix(self):
    return self.prefix + '/' + self.nick + '/' + self.uid

  def __str__(self):
    class UserEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
    return json.dumps(self, cls = UserEncoder)

  @classmethod
  def from_string(self, str_user):
    def as_user(dct):
      return User(dct['nick'], dct['prefix'], dct['uid'])
    
    return json.loads(str_user, object_hook = as_user)

class RemoteUser(User, StateObject):
  (Stopped, Probing, Streaming) = range(3)
  def __init__(self, user, *args, **kwargs):
    super(RemoteUser, self).__init__(user.nick, user.prefix, user.uid, *args, **kwargs)
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = self.__class__.Stopped
    self.timeouts = 0
    self.ice_candidate_msg = None
    self.sdp_sent = False
    self.stun_username = None

  def set_ice_candidate_msg(self, candidate_msg):
    self.ice_candidate_msg = candidate_msg

  def set_sdp_sent(self):
    self.sdp_sent = True

  def reset(self):
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = self.__class__.Stopped
    self.timeouts = 0

  def get_prescence(self):
    if (self.is_active()):
      return User.Unavailable
    else:
      return User.Available

  def __eq__(self, other):
    if self is None and other is not None:
      return False
    elif self is None and other is None:
      return True
    elif self is not None and other is None:
      return False
    else:
      return (self.nick == other.nick and self.preifx == other.prefix and self.uid == other.uid)
    

if __name__ == '__main__':
  u = User('hi', '/hi', 'lkasdjf')
  print User.from_string(str(u))
  print u.get_media_prefix()
  print u.get_sdp_prefix()
  print u.get_sync_prefix()

  ru = RemoteUser(u)
  print ru.get_prescence()
