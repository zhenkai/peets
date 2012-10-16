from user import User
from pyccn import Closure, CCN, Interest, Name
from pyccn._pyccn import CCNError
import pyccn
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

  def upcall(self, kind, upcallInfo):
    if kind in [Closure.UPCALL_CONTENT, Closure.UPCALL_CONTENT_UNVERIFIED]:
      return Closure.UPCALL_INTEREST_CONSUMED
    elif kind == Closure.UPCALL_INTEREST:
      pass
    elif kind == Closure.UPCALL_INTEREST_TIMED_OUT:
      return Closure.RESULT_REEXPRESS
    else:
      return Closure.RESULT_OK


if __name__ == '__main__':
  roster1 = Roster('tester1', '/test/ucla.edu')
  roster2 = Roster('tester2', '/test/ucla.edu')
