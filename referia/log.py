import os
import logging

class Logger():
    def __init__(self, name=None, level=20, filename="referia.log", directory="."):
        if level == "debug":
            self.level = logging.DEBUG
        elif level == "info":
            self.level = logging.INFO
        elif level == "warning":
            self.level = logging.WARNING
        elif level == "error":
            self.level = logging.ERROR
        elif level == "critical":
            self.level = logging.CRITICAL
        else:
            # For backwards compatability allowing direct specificaiton of a numeric level
            self.level = level
            
            
        self.filename = filename
        self.name = name
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s'
        logging.basicConfig(level=self.level, filename=os.path.join(directory,filename), format=format)
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

