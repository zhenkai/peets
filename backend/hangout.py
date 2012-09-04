from user import User, RemoteUser
from time import time

class Hangout(object):
  ''' Store the information of a hangout '''  

  default_broadcast_prefix = '/ndn/broadcast'

  def __init__(self, name, owner, email='unknown', 
              broadcast_prefix = default_broadcast_prefix):
    self.name = name
    self.owner = owner
    self.email = email
    self.broadcast_prefix = broadcast_prefix

  def get_name(self):
    return self.name

  def get_owner(self):
    return self.owner

  def get_email(self):
    return email


class RemoteHangout:
  ''' Store the information of a hangout announced by remote parties '''
  
  default_ttl = 60

  def __init__(self, name, owner, email = 'unknown', ttl = default_ttl):
    super(RemoteHangout, self).__init__(name, owner, email)
    self.timestamp = time()
    self.ttl = ttl

  def is_active(self):
    return (time() - self.timestamp < self.ttl)

  def refresh_timestamp(self):
    self.timestamp = time()
