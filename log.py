import logging
import threading
import os

class Logger(object):
  ''' A global logging facility for peets backend '''

  __filename = '/tmp/peets/backend.log'
  __lock = threading.Lock()

  dir_name = os.path.dirname(__filename)
  if not os.path.exists(dir_name):
    os.makedirs(dir_name)

  @staticmethod
  def get_logger(name, filename = __filename):
    logger = logging.getLogger(name)

    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s'\
                                  + ' - %(message)s')
    # write to file
    fh = logging.FileHandler(filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # write to stdout
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    return logger
    
