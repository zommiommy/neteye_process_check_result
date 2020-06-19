import sys

from ..rest_requests import *
from ..utils import retry, logger

@retry()
def create_host(args):
    logger.info("[CH] Creating host")
    status_code, data, text = create_host_request(args)

    if status_code == 200:
        logger.info("[CH] OK")
        return data

    logger.info("[CH] KO")
    sys.exit(2)