from time import time

class StateObject(object):
  ''' store the information of a soft-state object'''

  default_ttl = 60

  def __init__(self, *args, **kwargs):
    ''' somehow, this must also calls super in order for all 
        base classes to be initialized when the subclass calls
        its super init function'''
    super(StateObject, self).__init__()
    self.timestamp = kwargs.get('timestamp', time())
    self.ttl = kwargs.get('ttl', StateObject.default_ttl)

    print "Init StateObject"

  def is_active(self):
    return (time() - self.timestamp < self.ttl)

  def refresh_timestamp(self):
    self.timestamp = time()
