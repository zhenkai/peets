from pyccn import Closure, CCN, Interest, Name, EventLoop, ContentObject
from pyccn._pyccn import CCNError
import pyccn
from thread import start_new_thread
from log import Logger

class CcnxSocket(object):
  ''' A socket like handler for ccnx operations.
      Runs a simple event loop and handles set interest filter, send interest,
      and publish data. 
  '''

  __logger = Logger.get_logger('CcnxSocket')

  def __init__(self, *args, **kwargs):
    super(CcnxSocket, self).__init__()
    self.ccnx_key = CCN.getDefaultKey()
    self.ccnx_key_locator = pyccn.KeyLocator(self.ccnx_key)
    self.ccnx_handle = CCN() 
    self.event_loop = EventLoop(self.ccnx_handle)
    start_new_thread(event_loop.run) 

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

    si = get_signed_info(freshness)
    co.signedInfo = si

    co.sign(self.ccnx_key)
    self.ccnx_handle.put(co)
