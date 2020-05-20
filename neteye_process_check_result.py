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

####################################################################################################
# Constants
####################################################################################################
NETEYE_URL = """https://monitor.irideos.it:5665"""
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
            with open(path.format(**args).replace(" ", "_"), "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                result = function(args)
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

def create_host_request(args):
    url = "{neteye_url}/v1/objects/hosts/{host}".format(
        neteye_url=NETEYE_URL,
        host=urllib.quote(args["host"]).replace("/", "%2F")
    )
    logging.info("[HC] creating host on url %s", url)

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
        auth=(USER, PW), verify=False,
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
        host=urllib.quote(args["host"]).replace("/", "%2F"),
        service=urllib.quote(args["service"]).replace("/", "%2F"),
    )
    logging.info("[SC] creating service on url %s", url)

    data = {
            "templates":[args["service_template"]],
            "attrs":{
            }
    }

    r = requests.put(
        url,
        json=data,
        auth=(USER, PW), verify=False,
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
    logging.info("[PC] process_check_result on url %s", url)

    data = {
            "service": "{host}!{service}".format(**args),
            "exit_status":args["exit_status"],
            "plugin_output":args["plugin_output"],
            "check_source":os.uname()[1],
        }

    r = requests.post(
        url,
        json=data,
        auth=(USER, PW), verify=False,
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
        logging.info("[HC] OK : %s", data)
        return data

    logging.warning("[HC] got error: %s", text)
    sys.exit(2)


@lock("/var/lock/process_check_result_{service}_{host}.lock")
@retry()
def create_service(args):
    status_code, data, text = create_service_request(args)

    if status_code == 200:
        logging.info("[SC] OK : %s", data)
        return data
    
    logging.warning("[SC] Error : %s", text.replace("\n", ""))
    create_host(args)

@retry()
def process_check_result(args):
    status_code, data, text = process_check_result_request(args)
    if status_code == 200 and data["results"] != []:
        logging.info("[PC] OK : %s", data)
        return data

    logging.warning("[PC] Error : %s", text.replace("\n", ""))
    create_service(args)
    

####################################################################################################
# Arguments parsing
####################################################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Execute Icinga2's process check result and, if needed, create hostname and/or service"
    )
    parser.add_argument("host", type=str, help="")
    parser.add_argument("host_template", type=str, help="")
    parser.add_argument("service", type=str, help="")
    parser.add_argument("service_template", type=str, help="")
    parser.add_argument("plugin_output", type=str, help="")
    parser.add_argument("exit_status", type=int, help="")
    parser.add_argument("log-file", type=str, help="")

    args = vars(parser.parse_args())

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter("{uuid} %(levelname)s %(asctime)-15s %(message)s".format(uuid=uuid.uuid4()))

    shandler = logging.StreamHandler(sys.stdout)
    shandler.setLevel(logging.INFO)
    shandler.setFormatter(formatter)
    logger.addHandler(shandler)

    fhandler = logging.FileHandler(os.path.join("/neteye/shared/tornado/data/archive/", args["log_file"]))
    fhandler.setLevel(logging.INFO)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)

    # Disable --insecure warnings
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    logging.info("START")
    data = process_check_result(args)
    logging.info("[PC] OK : %s", data["results"])
    logging.info("STOP")