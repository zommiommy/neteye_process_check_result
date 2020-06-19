from multiprocessing import Manager, Queue, cpu_count
import os
from flask import Flask, request
from uuid import uuid4

from .utils import logger, disable_warnings, setup_logger
from .settings import get_settings
from .proxy_utils import schedule_process_check_result, ExecutorsCreator

####################################################################################################
# Routes
####################################################################################################

def process_check_result_endpoint_builder(task_queue, responses_results):
    def process_check_result_endpoint():
        args = request.json
        args["auth"] = tuple(args["auth"])
        print("Got request from %s"%args)
        return schedule_process_check_result(args, task_queue, responses_results)
    return process_check_result_endpoint

####################################################################################################
# Start
####################################################################################################

def run_proxy(port=9966):
    settings = get_settings(get_auth=False)
    setup_logger(settings["log_path"], "process_check_result_proxy.log", uuid4())
    # Create the syncrhonized data structures
    manager = Manager()
    responses_results = manager.dict()
    task_queue = Queue()

    requests_executor = ExecutorsCreator(task_queue, responses_results)
    requests_executor.start()
    # Start the http server
    app = Flask(__name__)
    app.route('/', methods=["POST"])(
        process_check_result_endpoint_builder(task_queue, responses_results)
    )
    app.run(host = '0.0.0.0', port=settings["proxy_port"])
