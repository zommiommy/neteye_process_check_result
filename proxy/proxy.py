import os
import re
import sys
import json
import time
from time import sleep, clock
import requests
from flask import Flask, request
from pprint import pprint
from multiprocessing import Manager, Queue, cpu_count
from threading import Thread
from uuid import uuid4

####################################################################################################
# Globals
####################################################################################################
app = Flask(__name__)
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))
NETEYE_URL = """"https://monitor.irideos.it:5665"""

####################################################################################################
# Decorators
####################################################################################################

def lock(path):
    """I have already checked, the unlock works even if the subfunction exits with sys.exit"""
    def lock_internal(function):
        def wrapped(args):
            args["hostb64"] = urlsafe_b64encode(args["host"].encode())
            args["serviceb64"] = urlsafe_b64encode(args["service"].encode())
            lock_path = path.format(**args)
            with open(lock_path, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN) 
                return result
        return wrapped
    return lock_internal

def retry(max_times=30, sleep_time=3):
    def retry_decorator(function):
        def wrapped(*args, **kwargs):
            for _ in range(max_times):
                try:
                    result = function(*args, **kwargs)
                    if result is not None:
                        return result
                except requests.exceptions.Timeout:
                    logging.warning("The function %s went in timeout", function.__name__)
                sleep(sleep_time)
            logging.warning(" [EXIT] %s reached max number of tries from the arguments %s", function.__name__, args)
            sys.exit(2)
        return wrapped
    return retry_decorator

####################################################################################################
# Requests
####################################################################################################

def check_service(args):
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
        logging.info("[CS] OK")
        return True

    logging.warning("[CS] Error : %s", r.text.replace("\n", ""))
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
    status_code, data, text = create_host_request(args)

    if status_code == 200:
        return 200, text

    return 500, text


@lock("/var/lock/process_check_result_{serviceb64}_{hostb64}.lock")
@retry()
def create_service(args):
    if check_service(args):
        return 200, "SERVICE EXISTS"
    status_code, data, text = create_service_request(args)

    if status_code == 200:
        return data

    if "already exists" in text:
        return data

    status_code, data, text = create_host(args)
    if status_code != 200:
        return status_code, text

@retry()
def process_check_result(args):
    status_code, data, text = process_check_result_request(args)
    if status_code == 200 and data["results"] != []:
        return status_code, data

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
                _id = task.pop("id")

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
        return schedule_process_check_result(request.json, task_queue, responses_results)

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