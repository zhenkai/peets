from user import User
from pyccn import Closure, CCN
from pyccn._pyccn import CCNError
from log import Logger

class Roster(Closure):
  ''' Keep a roster for a hangout '''
  _logger = Logger.get_logger('Roster')

  def __init__(self, name, prefix = '/', handle = None):
    self.name = name
    self.prefix = prefix
    self.users = {}
    if handle is None:
      try:
        self.handle = CCN()
      except CCNError as e:
        Roster._logger.error(e)
        raise e
    else:
      self.handle = handle

if __name__ == '__main__':
  Roster('tester', '/test/ucla.edu')
