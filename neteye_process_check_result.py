#!/bin/python
import os
import re
import sys
import uuid
import fcntl
import urllib
import logging
import requests
import argparse
from time import sleep
from base64 import urlsafe_b64encode

try:
    from time import clock
    timestamp_funciton = clock
except ImportError:
    from time import perf_counter_ns
    timestamp_funciton = perf_counter_ns
    

####################################################################################################
# Constants
####################################################################################################
NETEYE_URL = """https://monitor.irideos.it:5665""" # MUST be https
PROXY_URL  = """http://127.0.0.1:9966""" # MUST be http
USER="director"

PW_FILE="/neteye/shared/tornado/data/director-user.conf"
with open(PW_FILE) as f:
    match = re.search(r"password *= *\"(.+)\"", f.read())
    if match:
        PW = match.group(1)
    else:
        print("CANNOT FIND PASSWORD")
        sys.exit(-1)
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
                result = function(*args)
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

def proxy_request(args):
    args["epoch"] = timestamp_funciton()
    r = requests.post(
        PROXY_URL,
        json=args, verify=False,
        headers={
            "Accept": "application/json"
        }
    )
    return r.status_code, r.text

####################################################################################################
# Functions
####################################################################################################

@retry()
def create_host(args):
    logger.info("[CH] Creating host")
    status_code, data, text = create_host_request(args)

    if status_code == 200:
        logger.info("[CH] OK")
        return data

    logger.info("[CH] KO")
    sys.exit(2)


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


@retry()
def process_check_result(args):
    logger.info("Doing process_check_results")
    # Try to do the process_check_result
    status_code, data, text = process_check_result_request(args)
    if status_code == 200 and data["results"] != []:
        logger.info("process_check_results OK")
        return data
        
    logger.info("process_check_results KO")
    # if It fails delegate it to the proxy so that it can create the service
    # and/or host
    logging.info("Dispatching the request to the proxy")
    status_code, text = proxy_request(args)
    if status_code == 200:
        logger.info("process_check_results OK")
        return text

    logger.info("process_check_results KO")

    # if the proxy fails or it's not available, create service and host
    # This is the last resort because neteye has bugs that might lose the data
    # we send
    if not check_service(args):
        create_service(args)
        sleep(0.2)
        

####################################################################################################
# Arguments parsing
####################################################################################################
if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    parser = argparse.ArgumentParser(
        description="Execute Icinga2's process check result and, if needed, create hostname and/or service"
    )
    parser.add_argument("host", type=str, help="")
    parser.add_argument("host_template", type=str, help="")
    parser.add_argument("service", type=str, help="")
    parser.add_argument("service_template", type=str, help="")
    parser.add_argument("plugin_output", type=str, help="")
    parser.add_argument("exit_status", type=int, help="")
    parser.add_argument("log_file", type=str, help="")

    args = vars(parser.parse_args())
    args["auth"] = (USER, PW)
    args["check_source"] = os.uname()[1]
    print(args)
    log_level = logging.INFO

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logging.addLevelName(logging.WARNING, 'WARN')
    
    formatter = logging.Formatter("{uuid} %(levelname)s %(asctime)-15s %(message)s".format(uuid=uuid.uuid4()))

    shandler = logging.StreamHandler(sys.stdout)
    shandler.setLevel(log_level)
    shandler.setFormatter(formatter)
    logger.addHandler(shandler)

    fhandler = logging.FileHandler(os.path.join("/neteye/shared/tornado/data/archive/", args["log_file"]))
    fhandler.setLevel(log_level)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)

    # Disable --insecure warnings---------------------------//////////////////////////////////////////////////////mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm

    logging.info("START")
    data = process_check_result(args)
    logging.info("STOP")