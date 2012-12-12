import logging
import os
'''
.. module:: log
   :platform: Mac OS X, Linux
   :synopsis: A singleton to provide logging for an peets proxy instance
.. moduleauthor:: Zhenkai Zhu <zhenkai@cs.ucla.edu>
'''

class Logger(object):
  ''' A global logging facility for peets proxy '''

  pid = os.getpid()
  __filename = '/tmp/peets/%s.log' % str(pid)

  dir_name = os.path.dirname(__filename)
  if not os.path.exists(dir_name):
    os.makedirs(dir_name)

  @staticmethod
  def get_logger(name):
    ''' Get the logger

    Args:
      name (str): the name of the owner of the logger, usually the class name

    Returns:
      A logger using the default configuration here with the name provided
    '''

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s'\
                                  + ' - %(message)s')
    # write to file
    fh = logging.FileHandler(Logger.__filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # write to stdout
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.WARN)
    logger.addHandler(ch)
    return logger
    


#if __name__ == '__main__':
#  logger = Logger.get_logger('RandomTest')
#  logger.debug("hello")
#  logger.info("world")

