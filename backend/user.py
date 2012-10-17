from stateobject import StateObject

class User(object):
  ''' Store the common information of a user '''
  Available, Unavailable = range(2)

  def __init__(self, nick, prefix, *args, **kwargs):
    ''' somehow, this must also calls super in order for all 
        base classes to be initialized when the subclass calls
        its super init function'''
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
    if (self.is_active()):
      return User.Unavailable
    else:
      return User.Available
    

if __name__ == '__main__':
  ru = RemoteUser("hi", "/hi")
  print ru.get_prescence()
