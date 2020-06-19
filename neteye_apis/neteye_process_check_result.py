#!/bin/python
import os
import sys
import logging
import argparse
from time import sleep
from uuid import uuid4

from .apis import process_check_result
from .utils import retry, is_proxy_up, proxy_request, disable_warnings
from .settings import get_settings
from .utils import logger, setup_logger

@retry()
def normal_execution(args):
    logger.info("Doing process_check_results")
    # if It fails delegate it to the proxy so that it can create the service
    # and/or host
    logger.info("Dispatching the request to the proxy")
    status_code, text = proxy_request(args)
    if status_code == 200:
        logger.info("process_check_results OK")
        return text

    logger.info("process_check_results KO")
    sleep(0.2)

def execute(args):
    logger.info("START")
    data = normal_execution(args)
    if data is None:
        logger.warn("Entering Recovery")
        result = process_check_result(args, recovery=True)
        if result is not None:
            logger.info("process_check_results OK")
            return result
    logger.info("STOP")

####################################################################################################
# Arguments parsing
####################################################################################################
def run_client():
    parser = argparse.ArgumentParser(
        description="Execute Icinga2's process check result and, if needed, create hostname and/or service"
    )
    parser.add_argument("host", type=str, help="")
    parser.add_argument("host_template", type=str, help="")
    parser.add_argument("service", type=str, help="")
    parser.add_argument("service_template", type=str, help="")
    parser.add_argument("plugin_output", type=str, help="")
    parser.add_argument("exit_status", type=int, help="")
    parser.add_argument("log_file", type=str, help="The name of the log that will be created")
    parser.add_argument("eventid", type=int, help="A progressive identifier that's used to order the requests")

    args = vars(parser.parse_args())
    client_id = uuid4()
    args["client_id"] = client_id    
    args["check_source"] = os.uname()[1]

    args_to_print = args.copy()
    args.update(get_settings())

    disable_warnings()

    setup_logger(args["log_path"], args["log_file"], client_id, logging.INFO)

    logger.info("Running with arguments %s"%args_to_print)

    execute(args)