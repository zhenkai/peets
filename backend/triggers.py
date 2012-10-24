# This file includes the customized triggers to be used by apscheduler

from datetime import datetime, timedelta
from math import ceil

from apscheduler.util import convert_to_datetime, timedelta_seconds
from apscheduler.scheduler import Scheduler
from apscheduler.triggers import IntervalTrigger
from random import uniform

class RandomizedIntervalTrigger(IntervalTrigger):
  def __init__(self, interval, start_date = None, randomize = None):
    super(RandomizedIntervalTrigger, self).__init__(interval, start_date)
    self.randomize = randomize

  def get_next_fire_time(self, start_date):
    if start_date < self.start_date:
      return self.start_date

    timediff_seconds = timedelta_seconds(start_date - self.start_date)
    next_interval_num = int(ceil(timediff_seconds / self.interval_length))
    if self.randomize is None:
      return self.start_date + self.interval * next_interval_num 
    else:
      return self.start_date + self.interval * next_interval_num + timedelta(seconds=self.randomize())

if __name__ == '__main__':
  def func():
    print "-- Hello --"

  def wrap(**options):
    sched = Scheduler()
    sched.start()
    seconds = 5
    interval = timedelta(seconds = seconds)
    #trigger = RandomizedIntervalTrigger(interval, randomize = lambda : uniform(seconds / 8, seconds / 4))
    trigger = RandomizedIntervalTrigger(interval)

    sched.add_job(trigger, func, None, None, **{} )

  wrap()
  from time import sleep
  i = 0
  while(True):
    sleep(0.5)
    i = i + 0.5
    print "Time = " + str(i)
  


