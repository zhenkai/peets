from stateobject import StateObject

class User(object):
  ''' Store the common information of a user '''
  Available, Unavailable = range(2)

  def __init__(self, nick, prefix, *args, **kwargs):
    super(User, self).__init__()
    self.nick = nick
    self.prefix = prefix

    print "Init User: %s %s" % (self.nick, self.prefix)

  def get_nick(self):
    return self.nick

  def get_prefix(self):
    return self.prefix


class RemoteUser(User, StateObject):
  def __init__(self, nick, prefix, *args, **kwargs):
    super(RemoteUser, self).__init__(nick, prefix, *args, **kwargs)

  def get_prescence(self):
    current_time = time()
    if (current_time - self.timestamp > self.ttl):
      return Unavailable
    else:
      return Available
    

if __name__ == '__main__':
  ru = RemoteUser("hi", "/hi")
