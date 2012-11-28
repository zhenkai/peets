import logging
import os

class Logger(object):
  ''' A global logging facility for peets backend '''

  pid = os.getpid()
  __filename = '/tmp/peets/%s.log' % str(pid)

  dir_name = os.path.dirname(__filename)
  if not os.path.exists(dir_name):
    os.makedirs(dir_name)

  @staticmethod
  def get_logger(name, filename = __filename):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - [%(name)s] - %(levelname)s'\
                                  + ' - %(message)s')
    # write to file
    fh = logging.FileHandler(filename)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # write to stdout
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
    


if __name__ == '__main__':
  logger = Logger.get_logger('RandomTest')
  logger.debug("hello")
  logger.info("world")

