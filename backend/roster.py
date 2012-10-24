from user import User, RemoteUser
from pyccn import Closure, CCN, Interest, Name
from pyccn._pyccn import CCNError
import pyccn
from log import Logger
from chronos import SimpleChronosSocket
from ccnxsocket import CcnxSocket
from message import PeetsMessage
from time import time, sleep
from softstate import FreshList, StateObject

class PeetsMsgClosure(Closure):
  ''' A closure for processing PeetsMessage content object''' 
  def __init__(self, msg_callback):
    super(PeetsMsgClosure, self).__init__()
    self.msg_callback = msg_callback

  def upcall(self, kind, upcallInfo):
    if kind == pyccn.UPCALL_CONTENT:
      print "Fetched data with name: " + str(upcallInfo.ContentObject.name)
      self.msg_callback(upcallInfo.Interest, upcallInfo.ContentObject)

    return pyccn.RESULT_OK

class Roster(FreshList):
  ''' Keep a roster for a hangout '''
  __logger = Logger.get_logger('Roster')


  def __init__(self, chatroom_prefix, join_callback, leave_callback, local_user_info, *args, **kwargs):
    super(Roster, self).__init__(self.refresh_self, leave_callback, *args, **kwargs)
    self.join_callback = join_callback
    self.leave_callback = leave_callback
    self.local_user_info = local_user_info
    self.joined = False
    self.session = int(time())
    self.ccnx_sock = CcnxSocket()
    self.ccnx_sock.start()
    self.chronos_sock = SimpleChronosSocket(chatroom_prefix, self.fetch_peets_msg)
    # probably it's also a good idea to pass in the ccnx_sock so that this class can share
    # a sock with others, but for now we're give it a luxury package including its own ccnx_sock

    self.peetsClosure = PeetsMsgClosure(self.process_peets_msg)

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
        ru = RemoteUser(msg.msg_from, prefix, msg.audio_prefix, audio_rate_hint = msg.audio_rate_hint, audio_seq_hint = msg.audio_seq_hint)
        self.add(prefix, ru)
        print "Invoking join callback"
        join_callback(ru)
      elif msg.msg_type == PeetsMessage.Hello:
        self.refresh_for(prefix)
        print "Hello received"
      elif msg.msg_type == PeetsMessage.Leave:
        self.delete(prefix)
        ru = RemoteUser(msg.msg_from, prefix, msg.audio_prefix, audio_rate_hint = msg.audio_rate_hint, audio_seq_hint = msg.audio_seq_hint)
        print "Invoking leave callback"
        leave_callback(ru)
      else:
        print "dafaq"
        pass
    except KeyError as e:
      Roster.__logger.error("PeetsMessage does not have type or from" + e)

  def refresh_self(self):
    nick, prefix, audio_prefix, audio_rate_hint, audio_seq_hint = self.local_user_info()
    msg_type = PeetsMessage.Hello if self.joined else PeetsMessage.Join
    msg = PeetsMessage(msg_type, nick, audio_prefix = audio_prefix, audio_rate_hint = audio_rate_hint, audio_seq_hint = audio_seq_hint)
    msg_str = msg.to_string()
    self.chronos_sock.publish_string(prefix, self.session, msg_str, StateObject.default_ttl)
    self.joined = True

  def leave(self):
    nick, prefix, audio_prefix, audio_rate_hint, audio_seq_hint = self.local_user_info()
    msg = PeetsMessage(PeetsMessage.Leave, nick)
    msg_str = msg.to_string()
    self.chronos_sock.publish_string(prefix, self.session, msg_str, StateObject.default_ttl)
    self.joined = False

    # clean up our footprint in the chronos sync tree
    def clean_up():
      self.chronos_sock.remove(prefix)

    # event loop thread should wait until we clean up
    self.schedule_next(0.5, clean_up)
    
    
if __name__ == '__main__':
  def join_callback(ru):
    print 'User %s joined' % ru.nick

  def leave_callback(ru):
    print 'User %s left' % ru.nick

  def user_local_info_1():
    return ('tom', '/tom', '/tom/audio', None, None)

  def user_local_info_2():
    return ('jerry', '/jerry', '/jerry/audio', None, None)

  print "------ Creating the first roster object ------"
  roster1 = Roster('/test/chat', join_callback, leave_callback, user_local_info_1)
  sleep(2)
  print "------ Creating the second roster object ------"
  roster2 = Roster('/test/chat', join_callback, leave_callback, user_local_info_2)

  #sleep(1)
  #roster2.refresh_self()

  #sleep(1)
  #roster2.leave()


