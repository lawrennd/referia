import logging

from .config import *

class Logger():
    def __init__(self, name=None, level=20, filename="referia.log"):
        self.level = level
        self.filename = filename
        self.name = name
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s'
        logging.basicConfig(level=level, filename=filename, format=format)
        self.logger = logging.getLogger(name)

    def debug(self, message):
        self.logger.debug(message)
        
    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

