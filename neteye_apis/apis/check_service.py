import sys

from ..rest_requests import *
from ..utils import retry, logger

def check_service(args):
    status_code, data, text = check_service_request(args)
    
    if status_code == 200:
        logger.info("%s [CS] OK"%args["id"])
        return True

    logger.warning("%s [CS] Error : %s"%(text.replace("\n", ""), args["id"]))
    return False