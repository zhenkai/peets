from pyccn import Closure, CCN, Interest, Name, EventLoop, ContentObject
import pyccn
from thread import start_new_thread
import select
#from log import Logger

class PollLoop(object):
  def __init__(self, handle, *args, **kwargs):
    super(PollLoop, self).__init__()
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
        outputs.append(fd)

      # this is a hack of pyccn. it uses internal method
      # defined in ccn_private.h.. maybe it's not a good idea
      timeout = min(self.handle.process_scheduled(), 20)
      # time out is in seconds
      select.select(inputs, [], [], 2)
      #select.select(inputs, outpus, [], 2000)

  def stop(self):
    self.running = False
  

class CcnxSocket(object):
  ''' A socket like handler for ccnx operations.
      Runs a simple event loop and handles set interest filter, send interest,
      and publish data. 
      Current only one ccnx handle is used, we can use multiple handles if needed,
      but there is no such need as of now.
  '''

#  __logger = Logger.get_logger('CcnxSocket')

  def __init__(self, *args, **kwargs):
    super(CcnxSocket, self).__init__()
    self.ccnx_key = CCN.getDefaultKey()
    self.ccnx_key_locator = pyccn.KeyLocator(self.ccnx_key)
    self.ccnx_handle = CCN() 
    self.event_loop = PollLoop(self.ccnx_handle)

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

  name1 = Name('/local/test1')
  content1 = 'Hello, world! 1'
  name2 = Name('/local/test2')
  content2 = 'Hello, world! 2'
  name3 = Name('/local/test3')
  content3 = 'Hello, world! 3'

  class TestClosure(Closure):
    def __init__(self):
      super(TestClosure, self).__init__()

    def upcall(self, kind, upcallInfo):
      print "In upcall, kind = " + str(kind)
      if kind == pyccn.UPCALL_CONTENT:
        print upcallInfo.ContentObject.content

      return pyccn.RESULT_OK

  from time import sleep

  sock1.publish_content(name1, content1, 200)
  sleep(1)
  sock1.publish_content(name2, content2, 200)
  sleep(1)
  sock1.publish_content(name3, content3, 200)
  sleep(1)

 # for i in range(10)[1:]:
 #   print "---- i = " + str(i) + ", sending two interests with interval " + str(i) + " seconds ----"
 #   sock2.send_interest(name, TestClosure())
 #   sleep(i)
 #   sock2.send_interest(name, TestClosure())
 #   sleep(i)

  print "---- sending interests seconds ----"
  sock2.send_interest(name1, TestClosure())
  sleep(5)
  print "---- sending interests seconds ----"
  sock2.send_interest(name2, TestClosure())

  sleep(5)
  print "---- sending interests seconds ----"
  sock2.send_interest(name3, TestClosure())
  sleep(1)
  print "Stopped fetching process"
