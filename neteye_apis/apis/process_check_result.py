from time import sleep
from ..rest_requests import *
from ..utils import retry, logger
from .create_service import create_service

@retry()
def process_check_result(args, recovery=False):
    logger.info("Doing process_check_results")
    # Try to do the process_check_result
    status_code, data, text = process_check_result_request(args)
    if status_code == 200 and data["results"] != []:
        logger.info("process_check_results OK")
        return data

    logger.info("process_check_results KO")

    if recovery:
        # if the proxy fails or it's not available, create service and host
        # This is the last resort because neteye has bugs that might lose the data
        # we send
        create_service(args)
        sleep(0.2)
        