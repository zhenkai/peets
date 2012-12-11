from pyccn import Closure, CCN, Interest, Name, EventLoop, ContentObject
import pyccn
from thread import start_new_thread
import select
from log import Logger
'''
.. module:: CcnxLoop
   : platform: Mac OS X, Linux
   : synopsis: A loop that runs ccn_run.

.. moduleauthor:: Zhenkai Zhu < zhenkai@cs.ucla.edu>

.. module:: CcnxSocket
   : platform: Mac OS X, Linux
   : synopsis: A socket like interface for interacting with PyCCN.

.. moduleauthor:: Zhenkai Zhu < zhenkai@cs.ucla.edu>

.. module:: PeetsClosure
   : platform: Mac OS X, Linux
   : synopsis: A common closure class so user only needs to define the callback. Closure is required by PyCCN.

.. moduleauthor:: Zhenkai Zhu < zhenkai@cs.ucla.edu>
'''

class CcnxLoop(object):
  ''' A loop that runs ccn_run
  This is going to be scheduled in a separate thread
  '''
  def __init__(self, handle, *args, **kwargs):
    '''
    Args:
      handle (PyCCN.CCN): the handle to be used in the loop
    '''
    super(CcnxLoop, self).__init__()
    self.handle = handle
    self.running = False

  def run(self):
    '''
    Start the loop; use select.select to watch the handle for input and output;
    runs ccn_run if there is input/output or select timeout
    '''
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
      try:
        select.select(inputs, outputs, [], 0.05)
      except TypeError:
        # sometimes when use Ctrl-C to kill the process
        # it would have TypeError: an integer is required
        # have no idea what is the problem yet
        # but since we are shutting down, so probably it's ok 
        # to ignore this problem
        pass

  def stop(self):
    '''
    Stop the loop
    '''
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
    '''
    Creates a socket. As of now, we try to get the ccnx key from the default location
    '''
    super(CcnxSocket, self).__init__()
    self.ccnx_key = CCN.getDefaultKey()
    self.ccnx_key_locator = pyccn.KeyLocator(self.ccnx_key)
    self.ccnx_handle = CCN() 
    self.event_loop = CcnxLoop(self.ccnx_handle)

  def get_signed_info(self, freshness):
    '''
    Get signed info to be included in the Content Object
    Args:
      freshness (int): the freshness of the Content Object in seconds

    Returns:
      a PyCCN.SignedInfo object 
    '''
    si = pyccn.SignedInfo()
    si.publisherPublicKeyDigest = self.ccnx_key.publicKeyID
    si.type = pyccn.CONTENT_DATA
    si.freshnessSeconds = freshness
    si.keyLocator = self.ccnx_key_locator
    return si

  def get_pyccn_name(self, name):
    '''Get a valid name for PyCCN. This is useful when the name string is encoded as unicode, as is the usual case in Python. However, PyCCN has problem handling unicode names, raising TypeError as a result.
    
    Args:
      name (str): the name string
    
    Returns:
      An ascii encoded name string
    '''
    if isinstance(name, unicode):
      return Name(name.encode('ascii', 'ignore'))
    else:
      return Name(name)
    

  def publish_content(self, name, content, freshness = 5):
    '''Publish the data as a Content Object
    
    Args:
      name (str): the name string
      content (bytes): the data bytes

    Kwargs:
      freshness (int): the freshness in seconds for the Content Object
    '''
    co =  ContentObject()
    co.name = self.get_pyccn_name(name)
    co.content = content

    si = self.get_signed_info(freshness)
    co.signedInfo = si

    co.sign(self.ccnx_key)
    self.ccnx_handle.put(co)

  def send_interest(self, name, closure, template = None):
    '''Send Interest

    Args:
      name (str): the name string
      closure (PyCCN.Closure): the closure that includes the callbacks to be used by PyCCN for this Interest

    Kwargs:
      template (PyCCN.Interest): the template for the additional field to be carried in the Interest, such as ChildSelector, Lifetime, AnswerOrigin, etc..
    '''
    n = self.get_pyccn_name(name)
    self.ccnx_handle.expressInterest(n, closure, template)
    
  def register_prefix(self, prefix, closure):
    '''Register the prefix under which the user wishes to receive Interests

    Args:
      prefix (str): the prefix name string
      closure (PyCCN.Closure): the closure that includes the callbacks to be used by PyCCN when an Interest with such prefix comes
    '''
    p = self.get_pyccn_name(prefix)
    self.ccnx_handle.setInterestFilter(p, closure)

  def start(self):
    '''Start the CcnxLoop
    '''
    start_new_thread(self.event_loop.run, ())

  def stop(self):
    '''Stop the CcnxLoop
    '''
    self.event_loop.stop()

class PeetsClosure(Closure):
  ''' A closure for processing PeetsMessage content object

  Note: If the subclass of pyccn.Closure is a inner class of some class, it would make ccn_run fail in py-chronos. The reason is unknown. I guess something fishy is happening when the pyccn c code try to call the closure upcall method when the closure class is not resolvable in global name space.
  '''
  def __init__(self, incoming_interest_callback = None, msg_callback = None, timeout_callback = None):
    '''Customize the PyCCN.Closure subclass
    Kwargs:
      incoming_interest_callback: the callback function to be used by PyCCN when an Interest for this closure comes; takes PyCCN.UpcallInfo.Interest as the input
      msg_callback: the callback function to be used by PyCCN when an ContentObject is fetched; takes PyCCN.UpcallInfo.Interest and PyCCN.UpcallInfo.ContentObject as inputs
      timeout_callback: the callback function to be used by PyCCN when the Interest times out; takes PyCCN.UpcallInfo.Interest as the input
    
    *Note* that *timeout_callback* should return some ccnx upcall return value, e.g. pyccn.UPCALL_REEXPRESS is the user wants the Interest to be re-expressed
    '''
    super(PeetsClosure, self).__init__()
    self.incoming_interest_callback = incoming_interest_callback
    self.msg_callback = msg_callback
    self.timeout_callback = timeout_callback

  def upcall(self, kind, upcallInfo):
    '''Override the upcall function of the base class
    This function will be used by PyCCN whenever there is an upcall event
    '''
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

#if __name__ == '__main__':
#  from time import sleep, time
#  sock1 = CcnxSocket()
#  sock2 = CcnxSocket()
#  sock1.start()
#  sock2.start()
#
#  name = '/local/test1'
#  content = 'Hello, world!'
#  
#
#  class TestClosure(Closure):
#    def __init__(self):
#      super(TestClosure, self).__init__()
#      self.requested_seq = 0
#      self.fetched_seq = 0
#      
#    def upcall(self, kind, upcallInfo):
##      print "In upcall, kind = " + str(kind)
#      if kind == pyccn.UPCALL_CONTENT:
#        print 'Got %s: %s' % (upcallInfo.ContentObject.name, upcallInfo.ContentObject.content)
#        name = upcallInfo.ContentObject.name
#        seq = int (str(name).split('/')[-1])
#        self.fetched_seq = seq
#        
#
#      return pyccn.RESULT_OK
#
#
#  sock1.publish_content(name, content, 200)
#
#  import thread  
#  print 'start testing pre-fetching'
#  prefix = '/local/pre/fetch'
#  closure = TestClosure()
#
#  # Note that we use different socks for sending interest and publishing data
#  # this is because, if we use only one sock, the pending interests sent by this sock
#  # would not be satisfied by the content published later by this sock
#  # however, if the content is published earlier than the interest is sent, then
#  # using one sock has no problem
#  def fetch():
#    counter = 0
#    while True:
#      if closure.requested_seq - closure.fetched_seq < 5:
#        name = prefix + '/' + str(counter)
#        closure.requested_seq = counter
#        counter += 1
#        sock2.send_interest(name, closure)
#        
#      sleep(0.1)
#
#  def publish():
#    counter = 0
#    while True:
#      name = prefix + '/' + str(counter)
#      counter += 1
#      content = '%s' % time()
#      sock1.publish_content(name, content, 5)
#      sleep(0.2)
#
#  thread.start_new_thread(fetch, ())
#      
#  sleep(2.5)
#  publish()
#  
#  print "Stopped fetching process"
