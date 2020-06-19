import os
import sys
import logging

logger = logging.getLogger(__name__)
logging.addLevelName(logging.WARNING, 'WARN')

def setup_logger(log_path, log_file, _id, log_level=logging.INFO):
    global logger
    logger.setLevel(log_level)
    
    formatter = logging.Formatter("{uuid} %(levelname)s %(asctime)-15s %(message)s".format(uuid=_id))

    shandler = logging.StreamHandler(sys.stdout)
    shandler.setLevel(log_level)
    shandler.setFormatter(formatter)
    logger.addHandler(shandler)

    fhandler = logging.FileHandler(os.path.join(log_path, log_file))
    fhandler.setLevel(log_level)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)