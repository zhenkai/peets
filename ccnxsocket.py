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
    self.ccnx_handle.expressInterest(Name(name), closure, template)
    
  def register_prefix(self, prefix, closure):
    self.ccnx_handle.setInterestFilter(Name(prefix), closure)

  def start(self):
    start_new_thread(self.event_loop.run, ())

  def stop(self):
    self.event_loop.stop()

class PeetsClosure(Closure):
  ''' A closure for processing PeetsMessage content object
  timeout_callback should return some ccnx upcall return value
  '''
  def __init__(self, incoming_interest_callback = None, msg_callback = None, timeout_callback = None):
    super(PeetsClosure, self).__init__()
    self.incoming_interest_callback = incoming_interest_callback
    self.msg_callback = msg_callback
    self.timeout_callback = timeout_callback

  def upcall(self, kind, upcallInfo):
    if kind == pyccn.UPCALL_CONTENT:
      if self.msg_callback is not None:
        self.msg_callback(upcallInfo.Interest, upcallInfo.ContentObject)
    elif kind == pyccn.UPCALL_INTEREST_TIMED_OUT:
      if self.timeout_callback is not None:
        return self.timeout_callback(upcallInfo.Interest)
    elif kind == pyccn.UPCALL_INTEREST:
      if self.incoming_interest_callback is not None:
        self.incoming_interest_callback(upcallInfo.Interest)
      
    return pyccn.RESULT_OK

if __name__ == '__main__':
  from time import sleep, time
  sock1 = CcnxSocket()
  sock2 = CcnxSocket()
  sock1.start()
  sock2.start()

  name = '/local/test1'
  content = 'Hello, world!'
  

  class TestClosure(Closure):
    def __init__(self):
      super(TestClosure, self).__init__()
      self.requested_seq = 0
      self.fetched_seq = 0
      
    def upcall(self, kind, upcallInfo):
#      print "In upcall, kind = " + str(kind)
      if kind == pyccn.UPCALL_CONTENT:
        print 'Got %s: %s' % (upcallInfo.ContentObject.name, upcallInfo.ContentObject.content)
        name = upcallInfo.ContentObject.name
        seq = int (str(name).split('/')[-1])
        self.fetched_seq = seq
        

      return pyccn.RESULT_OK


  sock1.publish_content(name, content, 200)

  import thread  
  print 'start testing pre-fetching'
  prefix = '/local/pre/fetch'
  closure = TestClosure()

  # Note that we use different socks for sending interest and publishing data
  # this is because, if we use only one sock, the pending interests sent by this sock
  # would not be satisfied by the content published later by this sock
  # however, if the content is published earlier than the interest is sent, then
  # using one sock has no problem
  def fetch():
    counter = 0
    while True:
      if closure.requested_seq - closure.fetched_seq < 5:
        name = prefix + '/' + str(counter)
        closure.requested_seq = counter
        counter += 1
        sock2.send_interest(name, closure)
        
      sleep(0.1)

  def publish():
    counter = 0
    while True:
      name = prefix + '/' + str(counter)
      counter += 1
      content = '%s' % time()
      sock1.publish_content(name, content, 5)
      sleep(0.2)

  thread.start_new_thread(fetch, ())
      
  sleep(2.5)
  publish()
  
  print "Stopped fetching process"
