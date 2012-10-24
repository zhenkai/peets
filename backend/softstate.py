from time import time
from threading import Timer, RLock
from random import randint
from log import Logger

class StateObject(object):
  ''' store the information of a soft-state object'''

#  default_ttl = 60
  default_ttl = 5

  def __init__(self, *args, **kwargs):
    super(StateObject, self).__init__()
    self.timestamp = kwargs.get('timestamp', time())
    self.ttl = kwargs.get('ttl', StateObject.default_ttl)

  def is_active(self):
    return (time() - self.timestamp < self.ttl)

  def refresh_timestamp(self):
    self.timestamp = time()

class FreshList(object):
  ''' a list of fresh StateObjects maintained in soft state fashion'''
  _logger = Logger.get_logger('FreshList')

  reap_interval = StateObject.default_ttl * 2
  def __init__(self, refresh_func, reap_callback, *args, **kwargs):
    super(FreshList, self).__init__()
    self.instances = dict() 
    self.refresh_func = refresh_func
    self.reap_callback = reap_callback
    # every operation to self.instances should grab self.__rlock first
    self.__rlock = RLock()

    # start reap 
    interval = FreshList.reap_interval + randint(0, FreshList.reap_interval / 4)
    self.schedule_next(interval, self.reap)

    # start refresh self shortly
    short_wait = 0.5 # seconds
    self.schedule_next(short_wait, self.refresh)


  def reap(self):
    self.__rlock.acquire()
    zombies = filter(lambda(k, state_object): not state_object.is_active(), self.instances.iteritems())
    self.instances = dict(filter(lambda (k, state_object): state_object.is_active(), self.instances.iteritems()))
    self.__rlock.release()
    map(lambda(k, state_object): self.reap_callback(state_object), zombies)
    
    # schedule the next reap
    interval = FreshList.reap_interval + randint(0, FreshList.reap_interval / 4)
    self.schedule_next(interval, self.reap)

  def refresh_for(self, k):
    self.__rlock.acquire()
    try:
      self.instances[k].refresh_timestamp()
    except KeyError as e:
      FreshList._logger.exception("Try to refresh non-exist state object")
      raise e
    finally:
      self.__rlock.release()

  def get(self, k):
    return self.instances.get(k, None)

  def add(self, k, state_object):
    self.__rlock.acquire()
    self.instances[k] = state_object
    self.__rlock.release()
    
  def delete(self, k):
    self.__rlock.acquire()
    try:
      del self.instances[k]
    except KeyError as e:
      FreshList._logger.exception("Try to del non-exist state object")
      raise e
    finally:
      self.__rlock.release()
  
  def refresh(self):
    self.refresh_func()

    interval = StateObject.default_ttl - randint(0, StateObject.default_ttl / 4)
    self.schedule_next(interval, self.refresh)
    
  def schedule_next(self, interval, func):
    t = Timer(interval, func)
    t.start()

