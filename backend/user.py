from time import time

class User(object):
  ''' Store the common information of a user '''
  Available, Unavailable = range(2)

  def __init__(self, nick, prefix):
    self.nick = nick
    self.prefix = prefix

  def get_nick(self):
    return self.nick

  def get_prefix(self):
    return self.prefix


class RemoteUser(User):
  default_ttl = 60
  ''' Store remote user information, particularly timestamp of last refresh '''
  def __init__(self, nick, prefix, ttl = default_ttl):
    super(RemoteUser, self).__init__(nick, prefix)
    self.timestamp = time()
    self.ttl = ttl

  def get_prescence(self):
    current_time = time()
    if (current_time - self.timestamp > self.ttl):
      return Unavailable
    else:
      return Available
  
  def refresh_timestamp(self):
    self.timestamp = time()
    
