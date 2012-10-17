from user import User, RemoteUser
from stateobject import StateObject

class Hangout(object):
  ''' Store the information of a hangout '''  

  default_broadcast_prefix = '/ndn/broadcast'

  def __init__(self, name, owner, email, *args, **kwargs):
    ''' somehow, this must also calls super in order for all 
        base classes to be initialized when the subclass calls
        its super init function'''
    super(Hangout, self).__init__()
    self.name = name
    self.owner = owner
    self.email = email
    self.broadcast_prefix = kwargs.get('broadcast_prefix', Hangout.default_broadcast_prefix)

    print "Init Hangout"

  def get_name(self):
    return self.name

  def get_owner(self):
    return self.owner

  def get_email(self):
    return email


class RemoteHangout(Hangout, StateObject):
  ''' Store the information of a hangout announced by remote parties '''
  
  def __init__(self, name, owner, email, *args, **kwargs):
    super(RemoteHangout, self).__init__(name, owner, email, *args, **kwargs)

if __name__ == '__main__':
  rh = RemoteHangout("hi", "hello", "zhenkai@ucla.edu")
