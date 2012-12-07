from time import time
from datetime import datetime, timedelta
from apscheduler.scheduler import Scheduler
from triggers import RandomizedIntervalTrigger
from random import uniform
from threading import RLock
from log import Logger

class StateObject(object):
  ''' store the information of a soft-state object'''

  default_ttl = 60

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
    self.scheduler = Scheduler()
    self.scheduler.start()

    # schedule periodic reap 
    reap_interval = FreshList.reap_interval
    self.scheduler.add_job(RandomizedIntervalTrigger(timedelta(seconds = reap_interval), randomize = lambda: uniform(0, reap_interval / 4)), self.reap, None, None, **{})

    # schedule refresh self 
    refresh_interval = 0.7 * StateObject.default_ttl
    self.scheduler.add_job(RandomizedIntervalTrigger(timedelta(seconds = refresh_interval), randomize = lambda: uniform(0, refresh_interval / 4)), self.refresh_func, None, None, **{})

  def schedule_next(self, interval, func):
    self.scheduler.add_date_job(func, datetime.now() + timedelta(seconds = interval))

  def shutdown(self, wait = False):
    self.scheduler.shutdown(wait = False)

  def reap(self):
    with self.__rlock:
      zombies = filter(lambda(k, state_object): not state_object.is_active(), self.instances.iteritems())
      self.instances = dict(filter(lambda (k, state_object): state_object.is_active(), self.instances.iteritems()))
    map(lambda(k, state_object): self.reap_callback(state_object), zombies)
    
  def announce_received(self, k):
    with self.__rlock:
      self.instances[k].refresh_timestamp()

  def __getitem__(self, k):
    with self.__rlock:
      return self.instances.get(k, None)

  def __setitem__(self, k, state_object):
    with self.__rlock:
      self.instances[k] = state_object
    
  def __delitem__(self, k):
    with self.__rlock:
      try:
        del self.instances[k]
      except KeyError as e:
        FreshList._logger.exception("Try to del non-exist state object")
        raise e

  def __len__(self):
    with self.__rlock:
      return len(self.instances)

  def clear(self):
    with self.__rlock:
      self.instances.clear()

  def has_key(self, key):
    with self.__rlock:
      return self.instances.has_key(key)

  def keys(self):
    with self.__rlock:
      return self.instances.keys()
    
  def values(self):
    with self.__rlock:
      return self.instances.values()

  def items(self):
    with self.__rlock:
      return self.instances.items()
