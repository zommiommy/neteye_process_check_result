import os
import sys
import logging

from uuid import uuid4

logger = logging.getLogger(__name__)

def setup_logger(log_path, log_file, log_level=logging.INFO):
    global logger
    logger.setLevel(log_level)
    logger.addLevelName(logger.WARNING, 'WARN')
    
    formatter = logger.Formatter("{uuid} %(levelname)s %(asctime)-15s %(message)s".format(uuid=uuid4()))

    shandler = logger.StreamHandler(sys.stdout)
    shandler.setLevel(log_level)
    shandler.setFormatter(formatter)
    logger.addHandler(shandler)

    fhandler = logger.FileHandler(os.path.join(log_path, log_file))
    fhandler.setLevel(log_level)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)