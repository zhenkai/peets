from time import time
from datetime import datetime, timedelta
from apscheduler.scheduler import Scheduler
from triggers import RandomizedIntervalTrigger
from random import uniform
from threading import RLock
from log import Logger

'''
.. module:: softstate
  :platform: Mac OS X, Linux
  :synopsis: Managing a list of objects in softstate fashion, i.e. object gets removed if no refresh is received after certain time.

.. moduleauthor:: Zhenkai Zhu <zhenkai@cs.ucla.edu>

'''

class StateObject(object):
  ''' store the information of a soft-state object, which basically records the last timestamp of refresh and determines whether this object is timed out'''

  default_ttl = 60

  def __init__(self, *args, **kwargs):
    '''

    Kwargs:
      timestamp (float): the time in seconds since the epoch
      ttl (float): the time-to-live for state object
    '''
    super(StateObject, self).__init__()
    self.timestamp = kwargs.get('timestamp', time())
    self.ttl = kwargs.get('ttl', StateObject.default_ttl)

  def is_active(self):
    '''

    Returns:
      A boolean value to indicate whether or not this state object has been timed out.
    '''
    return (time() - self.timestamp < self.ttl)

  def refresh_timestamp(self):
    '''Set a new timestamp for this state object.
    '''
    self.timestamp = time()

class FreshList(object):
  ''' A dictionary of fresh StateObjects maintained in soft state fashion. (*NOTE: perhaps should rename it to FreshDict or something less misleading*).
  Timedout StateOjbect will be reaped, and a reap callback will to applied on them before reaping.
  A function that refresh the local user will be called periodically (*This SHOULD be refactored out of this class*).

  This list is protected by a recurisve lock for operation (both read and write).
  '''
  _logger = Logger.get_logger('FreshList')

  reap_interval = StateObject.default_ttl * 2
  def __init__(self, refresh_func, reap_callback, *args, **kwargs):
    '''
    Args:
      refresh_func: Callback function to refresh local user.
      reap_callback: Callback function to be applied to the StateObject to be reaped.
    '''
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
    '''A convenience function to schedule a task.

    Args:
      interval (float): The time from now to execute the task in seconds.
      func: The task to be executed.
    '''
    self.scheduler.add_date_job(func, datetime.now() + timedelta(seconds = interval))

  def shutdown(self, wait = False):
    '''Shutdown the scheduler of this object.
    '''
    self.scheduler.shutdown(wait = False)

  def reap(self):
    '''Checks the StateObjects and reap the ones that are timed out.
    '''
    with self.__rlock:
      zombies = filter(lambda(k, state_object): not state_object.is_active(), self.instances.iteritems())
      self.instances = dict(filter(lambda (k, state_object): state_object.is_active(), self.instances.iteritems()))
    map(lambda(k, state_object): self.reap_callback(state_object), zombies)
    
  def announce_received(self, k):
    '''Refresh stateobject when a refreshing announcement has been received for the object

    Args:
      k : the key for the state object to be refreshed
    '''
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
    '''Clear the dict.
    '''
    with self.__rlock:
      self.instances.clear()

  def has_key(self, key):
    '''Check whether the key exists in the current dict
    '''
    with self.__rlock:
      return self.instances.has_key(key)

  def keys(self):
    '''Get all keys.
    '''
    with self.__rlock:
      return self.instances.keys()
    
  def values(self):
    '''Get all values (stateobjects).
    '''
    with self.__rlock:
      return self.instances.values()

  def items(self):
    '''Get the key-value pairs.
    '''
    with self.__rlock:
      return self.instances.items()
