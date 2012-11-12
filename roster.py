from user import User, RemoteUser
from pyccn import Closure, CCN, Interest, Name
from pyccn._pyccn import CCNError
import pyccn
from log import Logger
from chronos import SimpleChronosSocket
from ccnxsocket import CcnxSocket, PeetsClosure
from message import PeetsMessage
from time import time, sleep
from softstate import FreshList, StateObject



class Roster(FreshList):
  ''' Keep a roster for a hangout '''
  __logger = Logger.get_logger('Roster')

  def __init__(self, chatroom_prefix, msg_callback, get_local_user, *args, **kwargs):
    super(Roster, self).__init__(self.refresh_self, self.reap_callback, *args, **kwargs)
    self.msg_callback = msg_callback
    self.get_local_user = get_local_user
    self.joined = False
    self.session = int(time())
    self.peetsClosure = PeetsClosure(self.process_peets_msg)
    self.ccnx_sock = CcnxSocket()
    self.ccnx_sock.start()
    self.chronos_sock = SimpleChronosSocket(chatroom_prefix, self.fetch_peets_msg)
    # send join after 0.5 second
    self.schedule_next(0.5, self.refresh_self)

  def fetch_peets_msg(self, name):
    print "Fetching name: " + name
    self.ccnx_sock.send_interest(Name(name), self.peetsClosure)
    
  def process_peets_msg(self, interest, data):
    ''' Assume the interest for peets msg would have a name like this:
    /user-data-prefix/peets_msg/session/seq
    This is because in the current implementation of chronos, it is the
    naming convention to have both session and seq
    '''
    name = data.name
    content = data.content
    prefix = '/'.join(str(name).split('/')[:-2])

    try:
      msg = PeetsMessage.from_string(content)
      if msg.msg_type == PeetsMessage.Join:
        print 'join from', msg.user
        ru = RemoteUser(msg.user)
        self.add(prefix, ru)
        print 'self.instances', self.instances
        self.msg_callback(msg)
      elif msg.msg_type == PeetsMessage.Hello:
        self.refresh_for(prefix)
      elif msg.msg_type == PeetsMessage.Leave:
        self.delete(prefix)
        self.msg_callback(msg)
      elif msg.msg_type == PeetsMessage.RTC:
        self.msg_callback(msg) 
      else:
        print "dafaq"
        pass
    except KeyError as e:
      Roster.__logger.exception("PeetsMessage does not have type or from")

  def reap_callback(self, remote_user):
    peets_msg = PeetsMessage(PeetsMessage.Leave, remote_user, None)
    self.msg_callback(peets_msg)

  def refresh_self(self):
    user = self.get_local_user()
    msg_type = PeetsMessage.Hello
    msg = PeetsMessage(msg_type, None, None)
    msg_str = str(msg)
    self.chronos_sock.publish_string(user.prefix, self.session, msg_str, StateObject.default_ttl)

  def publish_peets_msg(self, peets_msg):
    msg_str = str(peets_msg)
    self.chronos_sock.publish_string(peets_msg.user.prefix, self.session, msg_str, StateObject.default_ttl)
    if peets_msg.msg_type == PeetsMessage.Join:
      self.joined = True
      print 'joined', peets_msg
    elif peets_msg.msg_type == PeetsMessage.Leave:
      self.joined = False

      # clean up our footprint in the chronos sync tree
      def clean_up():
        self.chronos_sock.remove(peets_msg.user.prefix)

      # event loop thread should wait until we clean up
      self.schedule_next(0.5, clean_up)
    
    
if __name__ == '__main__':

  def msg_callback(msg):
    if msg.msg_type == PeetsMessage.Join:
      print 'User %s join' % msg.user.nick
    elif msg.msg_type == PeetsMessage.Leave:
      print 'User %s left' % msg.user.nick

  def user_local_info_1():
    return User('tom', '/roster/tom', '/roster/tom/audio', '12343')

  def user_local_info_2():
    return User('jerry', '/roster/jerry', '/roster/jerry/audio', 'lkasjdfs')

  print "------ Creating the first roster object ------"
  roster1 = Roster('/test/chat', msg_callback, user_local_info_1)
  msg1 = PeetsMessage(PeetsMessage.Join, user_local_info_1(), None)
  sleep(0.5)
  roster1.publish_peets_msg(msg1)
  sleep(2)
  print "------ Creating the second roster object ------"
  roster2 = Roster('/test/chat', msg_callback, user_local_info_2)
  msg2 = PeetsMessage(PeetsMessage.Join, user_local_info_2(), None)
  sleep(0.5)
  roster2.publish_peets_msg(msg2)

  sleep(10)
  roster1.shutdown()
  sleep(20)
  print "------ main thread should exit now ------"



