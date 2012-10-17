from user import User, RemoteUser
#from pyccn import Closure, CCN, Interest, Name
#from pyccn._pyccn import CCNError
#import pyccn
from log import Logger
from chronos import SimpleChronosSocket

class Roster(FreshList):
  ''' Keep a roster for a hangout '''
  _logger = Logger.get_logger('Roster')

  def __init__(self, chatroom_prefix, join_callback, leave_callback, refresh_func, *args, **kwargs):
    super(Roster, self).__init__(refresh_func = refresh_func, *args, **kwargs)
    self.join_callback = join_callback
    self.leave_callback = leave_callback
    self.sock = SimpleChronosSocket(chatroom_prefix, data_callback)

if __name__ == '__main__':
  pass
