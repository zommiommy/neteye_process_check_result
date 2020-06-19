
from ..rest_requests import *
from ..utils import lock, retry, logger

from .create_host import create_host
from .check_service import check_service

@lock("/var/lock/process_check_result_{serviceb64}_{hostb64}.lock")
@retry()
def create_service(args):
    logger.info("[CS] Creating the service")
    if check_service(args):
        return "SERVICE EXISTS"
    status_code, data, text = create_service_request(args)

    if status_code == 200:
        logger.info("[CS] OK")
        return data
    
    if "already exists" in text:
        logger.info("[CS] Service already exists")
        return data
    
    create_host(args)