import logging
import sys

###################
## Init app logger
logger = logging.getLogger('Poller')
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]'
)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(ch)