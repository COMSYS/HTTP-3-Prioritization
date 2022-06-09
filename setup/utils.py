import string
import random
import logging
import sys

def rand_str(n=10):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

class LoggingHelper:
    def __init__(self, timestr, nsid):
        self.nsid = nsid
        infolog = "logs/%s-%s.log"  % (nsid, timestr)
        log_format = "[%(asctime)-15s:" + nsid + "] %(message)s"
        log_formatter = logging.Formatter(log_format)
        logging.basicConfig(level=logging.INFO, filename=infolog, format=log_format)
        log_stream_handler = logging.StreamHandler()
        log_stream_handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(log_stream_handler)

        oldexcepthook = sys.excepthook
        def handle_exception(exc_type, exc_value, exc_traceback):
            logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
            oldexcepthook(exc_type, exc_value, exc_traceback)

        #sys.excepthook = handle_exception
    
    def addHandler(self, handler):
        log_format = "[%(asctime)-15s:" + self.nsid + "] %(message)s"
        log_formatter = logging.Formatter(log_format)
        handler.setFormatter(log_formatter)
        logging.getLogger().addHandler(handler)
    
    def removeHandler(self, handler):
        logging.getLogger().removeHandler(handler)