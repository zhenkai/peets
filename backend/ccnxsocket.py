from pyccn import Closure, CCN, Interest, Name, EventLoop, ContentObject
from pyccn._pyccn import CCNError
import pyccn
from thread import start_new_thread
from log import Logger

class CcnxSocket(object):
  ''' A socket like handler for ccnx operations.
      Runs a simple event loop and handles set interest filter, send interest,
      and publish data. 
      Current only one ccnx handle is used, we can use multiple handles if needed,
      but there is no such need as of now.
  '''

  __logger = Logger.get_logger('CcnxSocket')

  def __init__(self, *args, **kwargs):
    super(CcnxSocket, self).__init__()
    self.ccnx_key = CCN.getDefaultKey()
    self.ccnx_key_locator = pyccn.KeyLocator(self.ccnx_key)
    self.ccnx_handle = CCN() 
    self.event_loop = EventLoop(self.ccnx_handle)

  def get_signed_info(self, freshness):
    si = pyccn.SignedInfo()
    si.publisherPublicKeyDigest = self.ccnx_key.publicKeyID
    si.type = pyccn.CONTENT_DATA
    si.freshnessSeconds = freshness
    si.keyLocator = self.ccnx_key_locator
    return si

  def publish_content(self, name, content, freshness = 5):
    co =  ContentObject()
    co.name = Name(name)
    co.content = content

    si = self.get_signed_info(freshness)
    co.signedInfo = si

    co.sign(self.ccnx_key)
    self.ccnx_handle.put(co)

  def send_interest(self, name, closure, template = None):
    self.ccnx_handle.expressInterest(name, closure, template)
    
  def register_prefix(self, prefix, closure):
    self.ccnx_handle.setInterestFilter(prefix, closure)

  def start(self):
    start_new_thread(self.event_loop.run, ())

  def stop(self):
    self.event_loop.stop()


if __name__ == '__main__':
  sock1 = CcnxSocket()
  sock2 = CcnxSocket()
  sock1.start()
  sock2.start()

  name = Name('/local/test')
  content = 'Hello, world!'

  class TestClosure(Closure):
    def __init__(self):
      super(TestClosure, self).__init__()

    def upcall(self, kind, upcallInfo):
      if kind == pyccn.UPCALL_CONTENT:
        print upcallInfo.ContentObject.content

      return pyccn.RESULT_OK

  sock1.publish_content(name, content, 200)
  sock2.send_interest(name, TestClosure())
  from time import sleep
  print "Fetching with interval 1 second for 2 times"
  for i in xrange(2):
    sleep(1)
    sock2.send_interest(name, TestClosure())

  print "Fetching with interval 2 second for 2 times"
  for i in xrange(2):
    sleep(2)
    sock2.send_interest(name, TestClosure())

  print "Fetching with interval 3 second for 2 times"
  for i in xrange(2):
    sleep(3)
    sock2.send_interest(name, TestClosure())

  print "Fetching with interval 4 second for 2 times"
  for i in xrange(2):
    sleep(4)
    sock2.send_interest(name, TestClosure())

  print "Fetching with interval 5 second for 2 times"
  for i in xrange(2):
    sleep(5)
    sock2.send_interest(name, TestClosure())

  sleep(1)
  print "Stopped fetching process"
