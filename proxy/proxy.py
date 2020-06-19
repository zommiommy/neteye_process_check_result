import argparse
import fcntl
import json
import logging
import os
import re
import sys
import time
import urllib
import uuid
from base64 import urlsafe_b64encode
from multiprocessing import Manager, Queue, cpu_count
from pprint import pprint
from threading import Thread
from time import sleep
from uuid import uuid4

import requests
from flask import Flask, request

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

####################################################################################################
# Globals
####################################################################################################
app = Flask(__name__)
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
NETEYE_URL = """https://monitor.irideos.it:5665"""

####################################################################################################
# Decorators
####################################################################################################

def retry(max_times=30, sleep_time=3):
    def retry_decorator(function):
        def wrapped(*args, **kwargs):
            for _ in range(max_times):
                try:
                    result = function(*args, **kwargs)
                    if result is not None:
                        return result
                except requests.exceptions.Timeout:
                    logger.warning("The function %s went in timeout", function.__name__)
                sleep(sleep_time)
            text = " [EXIT] %s reached max number of tries from the arguments %s", function.__name__, args
            logger.warning(text)
            return 500, text
        return wrapped
    return retry_decorator

####################################################################################################
# Requests
####################################################################################################

def check_service(args):
    logger.info("%s [CS] Check if the service exists"%args["id"])
    url = "{neteye_url}/v1/objects/services/{host}!{service}".format(
        neteye_url=NETEYE_URL,
        host=args["host"].replace("/", "%2F"),
        service=args["service"].replace("/", "%2F"),
    )

    data = {
            "templates":[args["service_template"]],
    }

    r = requests.get(
        url,
        json=data,
        auth=args["auth"], verify=False,
        headers={
            'Accept': 'application/json',
        }
    )

    if r.status_code == 200:
        logger.info("%s [CS] OK"%args["id"])
        return True

    logger.warning("%s [CS] Error : %s"%(r.text.replace("\n", ""), args["id"]))
    return False

def create_host_request(args):
    url = "{neteye_url}/v1/objects/hosts/{host}".format(
        neteye_url=NETEYE_URL,
        host=args["host"].replace("/", "%2F")
    )

    data = {
            "templates":[args["host_template"]],
            "attrs":{
                "address":"127.0.0.1",
                "check_command":"hostalive",
            }
    }

    r = requests.put(
        url,
        json=data,
        auth=args["auth"], verify=False,
        headers={
            'Accept': 'application/json',
        }
    )

    try:
        data = r.json()
    except:
        data = r.text

    return r.status_code, data, r.text

def create_service_request(args):
    url = "{neteye_url}/v1/objects/services/{host}!{service}".format(
        neteye_url=NETEYE_URL,
        host=args["host"].replace("/", "%2F"),
        service=args["service"].replace("/", "%2F"),
    )

    data = {
            "templates":[args["service_template"]],
            "attrs":{
            }
    }

    r = requests.put(
        url,
        json=data,
        auth=args["auth"], verify=False,
        headers={
            'Accept': 'application/json',
        }
    )

    try:
        data = r.json()
    except:
        data = r.text

    return r.status_code, data, r.text

def process_check_result_request(args):
    url = NETEYE_URL +  "/v1/actions/process-check-result"

    data = {
            "service": "{host}!{service}".format(**args),
            "exit_status":args["exit_status"],
            "plugin_output":args["plugin_output"],
            "check_source":args["check_source"],
        }
        
    r = requests.post(
        url,
        json=data,
        auth=args["auth"], verify=False,
        headers={
            'Accept': 'application/json',
        }
    )
    
    try:
        data = r.json()
    except:
        data = r.text

    return r.status_code, data, r.text


####################################################################################################
# Functions
####################################################################################################

@retry()
def create_host(args):
    logger.info("%s [CH] Creating host"%args["id"])
    status_code, data, text = create_host_request(args)

    if status_code == 200:
        logger.info("%s [CH] OK"%args["id"])
        return 200, text

    logger.info("%s [CH] KO"%args["id"])
    return 500, text

@retry()
def create_service(args):
    logger.info("%s [CS] Creating the service"%args["id"])
    status_code, data, text = create_service_request(args)

    if status_code == 200:
        logger.info("%s [CS] OK"%args["id"])
        return data

    if "already exists" in text:
        logger.info("%s [CS] Service already exists"%args["id"])
        return data

    create_host(args)

@retry()
def process_check_result(args):
    logger.info("%s Doing process_check_results"%args["id"])
    status_code, data, text = process_check_result_request(args)
    if status_code == 200 and data["results"] != []:
        logger.info("%s process_check_results OK"%args["id"])
        return status_code, data

    logger.info("%s process_check_results KO"%args["id"])

    if not check_service(args):
        create_service(args)
        sleep(0.2)
        

####################################################################################################
# Ordered Synchronized queue executor
####################################################################################################

class RequestsExecutor(Thread):

    def __init__(self, queue, responses_results):
        super(RequestsExecutor, self).__init__()
        self.queue = queue
        self.responses_results = responses_results
        self.tasks = []
    
    def _recv_tasks(self):
        while not self.queue.empty() or self.tasks == []:
            self.tasks.append(self.queue.get())
            if len(self.tasks) < 5:
                sleep(0.3)
        self.tasks.sort()


    def run(self):
        try:
            while True:
                self._recv_tasks()

                epoch, task = self.tasks.pop(0)
                _id = task["id"]
                print("Executing task %s"%task)
                status_code, text = process_check_result(task)

                self.responses_results[_id] = {
                    "status_code":status_code,
                    "content":text
                }
        except KeyboardInterrupt:
            print("Stopped by user")


class ExecutorsCreator(Thread):
    def __init__(self, task_queue, responses_results):
        super(ExecutorsCreator, self).__init__()
        self.task_queue = task_queue
        self.responses_results = responses_results

    def _setup_queue(self, lock, tasks):
        if lock not in tasks:
            _queue = Queue()
            tasks[lock] = _queue
            RequestsExecutor(_queue, self.responses_results).start()

    def run(self):
        tasks = {}
        try:
            while True:
                epoch, task = self.task_queue.get()
                lock = (task["service"], task["host"])
                self._setup_queue(lock, tasks)
                tasks[lock].put((epoch, task))
        except KeyboardInterrupt:
            print("Stopped by user")
        

def schedule_process_check_result(params, task_queue, responses_results):
    _id = uuid4().hex
    params["id"] = _id

    task_queue.put((params.pop("epoch"), params))

    while _id not in responses_results:
        sleep(0.1)

    response = responses_results.pop(_id)
    return response["content"], response["status_code"]
    
####################################################################################################
# Routes
####################################################################################################

def process_check_result_endpoint_builder(task_queue, responses_results):
    @app.route('/', methods=["POST"])
    def process_check_result_endpoint():
        args = request.json
        args["auth"] = tuple(args["auth"])
        print("Got request from %s"%args)
        return schedule_process_check_result(args, task_queue, responses_results)

####################################################################################################
# Start
####################################################################################################

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    manager = Manager()
    responses_results = manager.dict()
    task_queue = Queue()
    requests_executor = ExecutorsCreator(task_queue, responses_results)
    requests_executor.start()
    process_check_result_endpoint_builder(task_queue, responses_results)
    app.run(host = '0.0.0.0', port = 9966, threaded=False, processes=10)
