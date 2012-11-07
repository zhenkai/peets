from pyccn import Closure, CCN, Interest, Name, EventLoop, ContentObject
import pyccn
from thread import start_new_thread
import select
from log import Logger

class CcnxLoop(object):
  def __init__(self, handle, *args, **kwargs):
    super(CcnxLoop, self).__init__()
    self.handle = handle
    self.running = False

  def run(self):
    self.running = True
    # select.poll() is disabled in Mac OS X.. dafaq?!
    #poller = select.poll()
    #poller.register(self.handle.fileno(), select.POLLIN | select.POLLOUT)
    inputs = [self.handle]
    while (self.running):
      self.handle.run(0)
      outputs = []
      if self.handle.output_is_pending():
        outputs.append(self.handle)

      # time out is in seconds
      select.select(inputs, outputs, [], 0.05)

  def stop(self):
    self.running = False
  

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
    self.event_loop = CcnxLoop(self.ccnx_handle)

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

class PeetsClosure(Closure):
  ''' A closure for processing PeetsMessage content object''' 
  def __init__(self, msg_callback):
    super(PeetsClosure, self).__init__()
    self.msg_callback = msg_callback

  def upcall(self, kind, upcallInfo):
    if kind == pyccn.UPCALL_CONTENT:
      print "Fetched data with name: " + str(upcallInfo.ContentObject.name)
      self.msg_callback(upcallInfo.Interest, upcallInfo.ContentObject)

    return pyccn.RESULT_OK

if __name__ == '__main__':
  sock1 = CcnxSocket()
  sock2 = CcnxSocket()
  sock1.start()
  sock2.start()

  name = Name('/local/test1')
  content = 'Hello, world!'

  class TestClosure(Closure):
    def __init__(self):
      super(TestClosure, self).__init__()

    def upcall(self, kind, upcallInfo):
      print "In upcall, kind = " + str(kind)
      if kind == pyccn.UPCALL_CONTENT:
        print upcallInfo.ContentObject.content

      return pyccn.RESULT_OK

  from time import sleep

  sock1.publish_content(name, content, 200)

  for i in range(10)[1:]:
    print "---- i = " + str(i) + ", sending two interests with interval " + str(i) + " seconds ----"
    sock2.send_interest(name, TestClosure())
    sleep(i)
    sock2.send_interest(name, TestClosure())
    sleep(i)

  print "Stopped fetching process"
