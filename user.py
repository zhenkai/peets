from softstate import StateObject

class User(object):
  ''' Store the common information of a user '''
  Available, Unavailable = range(2)

  def __init__(self, nick, prefix, *args, **kwargs):
    ''' somehow, this must also calls super in order for all 
        base classes to be initialized when the subclass calls
        its super init function

        The prefix here is the identity prefix for a user used
        in the chronos sync tree. It's not exactly the same as the
        audio prefix, but may be the prefix of the audio prefix
    '''
    super(User, self).__init__()
    self.nick = nick
    self.prefix = prefix


  def get_nick(self):
    return self.nick

  def get_prefix(self):
    return self.prefix


class RemoteUser(User, StateObject):
  def __init__(self, nick, prefix, audio_prefix, *args, **kwargs):
    super(RemoteUser, self).__init__(nick, prefix, *args, **kwargs)
    self.audio_prefix = audio_prefix

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
      return (self.nick == other.nick and self.preifx == other.prefix and self.audio_prefix == other.audio_prefix) 
    

if __name__ == '__main__':
  ru = RemoteUser("hi", "/hi")
  print ru.get_prescence()
