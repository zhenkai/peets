from time import time

class StateObject(object):
  ''' store the information of a soft-state object'''

  default_ttl = 60

  def __init__(self, timestamp, ttl = default_ttl):
    super(StateObject, self).__init__()
    self.timestamp = timestamp
    self.ttl = ttl

  def is_active(self):
    return (time() - self.timestamp < self.ttl)

  def refresh_timestamp(self):
    self.timestamp = time()
