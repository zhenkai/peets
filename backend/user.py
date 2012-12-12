from softstate import StateObject
import json

'''
.. module:: user
  :platform: Mac OS X, Linux
  :synopsis: Manage user information

.. moduleauthor:: Zhenkai Zhu <zhenkai@cs.ucla.edu>

'''

class User(object):
  ''' Store the common information of a user, regardless of local user or remote user '''

  Available, Unavailable = range(2)

  def __init__(self, nick, prefix, uid, *args, **kwargs):
    '''

    Args:
      nick (str): The nick name to be used by app
      prefix (str): The valid prefix for the user, SHOULD be routable
      uid (str): A unique string for this user

      somehow, this must also calls super in order for all 
      base classes to be initialized when the subclass calls
      its super init function
    '''
    super(User, self).__init__()
    self.nick = nick
    self.prefix = prefix
    self.uid = uid


  def get_nick(self):
    return self.nick

  def get_media_prefix(self):
    '''
    Returns:
      The prefix to be used for user's media data, i.e. RTP data
      
    '''
    return self.prefix + '/' + self.nick + '/' + self.uid + '/media'

  def get_ctrl_prefix(self):
    '''
    Returns:
      The prefix to be used for user's control data, including STUN message and RTCP message
    '''
    return self.prefix + '/' + self.nick + '/' + self.uid + '/ctrl'

  def get_sdp_prefix(self):
    '''
    Returns:
      The prefix to be used for user's sdp data
    '''
    return self.prefix + '/' + self.nick + '/' + self.uid + '/sdp'

  def get_sync_prefix(self):
    '''
    Returns:
      The prefix to be used by the sync module for this user
    '''
    return self.prefix + '/' + self.nick + '/' + self.uid

  def __str__(self):
    class UserEncoder(json.JSONEncoder):
      def default(self, obj):
        return obj.__dict__
    return json.dumps(self, cls = UserEncoder)

  @classmethod
  def from_string(self, str_user):
    '''Create a User object from the string representation.

    Args:
      str_user (str): The string representation of a User object.
    '''
    def as_user(dct):
      return User(dct['nick'], dct['prefix'], dct['uid'])
    
    return json.loads(str_user, object_hook = as_user)

class RemoteUser(User, StateObject):
  '''Inherit from User and StateObject. This is to store information about the remote users. 

  In addition to the data field in User, it adds several fields to represent the data streaming status of a remote user. E.g. self.requested_seq and self.fetched_seq are the highest sequence numbers for data Interests that have been send and Data that has been received so far. self.timeouts record the number of consecutive timeouts. 

  It also records other states for the remote user, like the ice candidate msg or whether the sdp has been sent. This is required because WebRTC requires to receive sdp before ice candidate msg, but the two may be received in the reverse order.

  It is also an object that could be put into a list managed in softstate fashion.
  '''
  (Stopped, Probing, Streaming) = range(3)
  def __init__(self, user, *args, **kwargs):
    '''

    Args:
      user (User): the user part of RemoteUser

    '''
    super(RemoteUser, self).__init__(user.nick, user.prefix, user.uid, *args, **kwargs)
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = self.__class__.Stopped
    self.timeouts = 0
    self.ice_candidate_msg = None
    self.sdp_sent = False

  def set_ice_candidate_msg(self, candidate_msg):
    '''Record the ice candidate msg in case we need it in the future
    '''
    self.ice_candidate_msg = candidate_msg

  def set_sdp_sent(self):
    '''Set the boolean flag to indicate that the sdp message for this user has been sent to webrtc
    '''
    self.sdp_sent = True

  def reset(self):
    '''Resets the data streaming related field to default. This should be called when a large number of timeouts have been experienced and the data fetch falls back to probing mode.
    '''
    self.requested_seq = 0
    self.fetched_seq = 0
    self.streaming_state = self.__class__.Stopped
    self.timeouts = 0

  def get_prescence(self):
    '''Get the remote user presence
    '''
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
