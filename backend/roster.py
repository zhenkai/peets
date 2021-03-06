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

'''
.. module:: roster
  :platform: Mac OS X, Linux
  :synopsis: Manage the roster of the conference participants using Chronos sync

.. moduleauthor:: Zhenkai Zhu <zhenkai@cs.ucla.edu>

'''


class Roster(FreshList):
  '''Manage the roster of the conference participants using Chronos sync.
  Additionally, it handles light-weight processing of the Peets Message.
  '''

  __logger = Logger.get_logger('Roster')
  (Init, Joined, Stopped) = range(3)

  def __init__(self, chatroom_prefix, msg_callback, get_local_user, *args, **kwargs):
    '''
    Args:
      chatroom_prefix (str): A broadcast prefix for the chatroom; this is used by Chronos for it's sync Interests.
      msg_callbck : The callback function when a Peets Message comes.
      get_local_user : A function that returns the local user information.
    '''

    super(Roster, self).__init__(self.announce, self.reap_callback, *args, **kwargs)
    self.msg_callback = msg_callback
    self.get_local_user = get_local_user
    self.status = self.__class__.Init
    self.session = int(time())
    self.peetsClosure = PeetsClosure(msg_callback = self.process_peets_msg)
    self.ccnx_sock = CcnxSocket()
    self.ccnx_sock.start()
    self.chronos_sock = SimpleChronosSocket(chatroom_prefix, self.fetch_peets_msg)
    # send join after 0.5 second
    self.schedule_next(0.5, self.announce)

  def fetch_peets_msg(self, name):
    '''A wrapper function for fetching peets msg. If the local user has stopped participanting, then don't fetch the peets msg.
    '''
    if self.status == self.__class__.Stopped:
      return 

    self.ccnx_sock.send_interest(name, self.peetsClosure)
    
  def process_peets_msg(self, interest, data):
    '''Process Peets Message. This is used as a callback for the PeetsClosure.

    Args:
      interest: The PyCCN.UpcallInfo.Interest.
      data: The PyCCN.UpcallInfo.ContentObject.

    Assume the interest for peets msg would have a name like this:
    /user-data-prefix/peets_msg/session/seq
    This is because in the current implementation of chronos, it is the
    naming convention to have both session and seq
    '''
    # do not process remove msg when stopped
    if self.status == self.__class__.Stopped:
      return

    #name = data.name
    content = data.content
    #prefix = '/'.join(str(name).split('/')[:-2])

    try:
      msg = PeetsMessage.from_string(content)
      uid = msg.user.uid
      if msg.msg_type == PeetsMessage.Join:
        #ru = RemoteUser(msg.user)
        #self[uid] = ru
        self.msg_callback(msg)
      elif msg.msg_type == PeetsMessage.Hello:
        try:
          self.announce_received(uid)
        except KeyError:
          self.__class__.__logger.info('Refresh announcement for unknown user %s, treating as Join', uid)
          #ru = RemoteUser(msg.user)
          #self[uid] = ru
          self.msg_callback(msg)

      elif msg.msg_type == PeetsMessage.Leave:
        #del self[uid]
        self.msg_callback(msg)
      elif msg.msg_type == PeetsMessage.Chat:
        self.msg_callback(msg)
      else:
        self.__class__.__logger.error("unknown PeetsMessage type")
    except KeyError as e:
      Roster.__logger.exception("PeetsMessage does not have type or from")

  # used by FreshList when zombie is reaped
  def reap_callback(self, remote_user):
    '''This is the reap callback for the FreshList. Do the clean up needed here when a remote user is considered left.

    Args:
      remote_user (RemoteUser): The remote user considered left by FreshList.
    '''
    peets_msg = PeetsMessage(PeetsMessage.Leave, remote_user)
    self.msg_callback(peets_msg)
    print self.get_local_user().nick, 'reaping', remote_user

  def announce(self):
    '''This is a function to announce/refresh the prescence of the local user to others. 
    '''
    if self.status == self.__class__.Stopped:
      return

    user = self.get_local_user()
    msg_type = PeetsMessage.Hello if self.status == self.__class__.Joined else PeetsMessage.Join
    msg = PeetsMessage(msg_type, user)
    msg_str = str(msg)
    self.chronos_sock.publish_string(user.get_sync_prefix(), self.session, msg_str, StateObject.default_ttl)
    self.status = self.__class__.Joined

  def leave(self):
    '''Tell remote users that the local user is leaving.
    '''
    user = self.get_local_user()
    msg_type = PeetsMessage.Leave
    msg = PeetsMessage(msg_type, user)
    msg_str = str(msg)
    self.chronos_sock.publish_string(user.get_sync_prefix(), self.session, msg_str, StateObject.default_ttl)
    self.status = self.__class__.Stopped

    # clean up our footprint in the chronos sync tree
    def clean_up():
      self.chronos_sock.remove(user.get_sync_prefix())
      print 'cleaning up'
      def clean_up():
        self.chronos_sock.stop()
        self.shutdown()

      self.schedule_next(0.5, clean_up)

    # event loop thread should wait until we clean up
    self.schedule_next(0.5, clean_up)
    
    
if __name__ == '__main__':

  def msg_callback_1(msg):
    global roster1
    if msg.msg_type == PeetsMessage.Join or msg.msg_type == PeetsMessage.Hello:
      print 'User %s join' % msg.user.nick
      print 'msg is %s' % msg
      roster1[msg.user.uid] = RemoteUser(msg.user)

    elif msg.msg_type == PeetsMessage.Leave:
      print 'User %s left' % msg.user.nick
      del roster1[msg.user.uid]

  def msg_callback_2(msg):
    global roster2
    if msg.msg_type == PeetsMessage.Join or msg.msg_type == PeetsMessage.Hello:
      print 'User %s join' % msg.user.nick
      print 'msg is %s' % msg
      roster2[msg.user.uid] = RemoteUser(msg.user)

    elif msg.msg_type == PeetsMessage.Leave:
      print 'User %s left' % msg.user.nick
      del roster2[msg.user.uid]

  def user_local_info_1():
    return User('tom', '/roster/tom', '12343')

  def user_local_info_2():
    return User('jerry', '/roster/jerry', 'lkasjdfs')

  print "------ Creating the first roster object ------"
  roster1 = Roster('/test/chat', msg_callback_1, user_local_info_1)
  msg1 = PeetsMessage(PeetsMessage.Join, user_local_info_1(), None)
  sleep(5)
  print "------ Creating the second roster object ------"
  roster2 = Roster('/test/chat', msg_callback_2, user_local_info_2)
  msg2 = PeetsMessage(PeetsMessage.Join, user_local_info_2(), None)

  sleep(10)
  roster2.leave()
  roster2 = None
  sleep(6)
  roster1.shutdown()
  sleep(6)
  print "------ main thread should exit now ------"



