#!/bin/python
import os
import re
import sys
import uuid
import time
import logging
import requests
import argparse
####################################################################################################
# Constants
####################################################################################################
NETEYE_URL = """monitor.irideos.it:5665"""
USER="director"

PW_FILE="/neteye/shared/icinga2/conf/icinga2/conf.d/director-user.conf"
with open(PW_FILE) as f:
    PW = f.read()
    

LOG_FILE = """/neteye/shared/tornado/data/archive/all/tornado_{rule}_creation.log"""

UUID = uuid.uuid4()
####################################################################################################
# Functions
####################################################################################################
def retry(max_times=4, sleep_time=1):
    def retry_decorator(function):
        def wrapped(*args, **kwargs):
            for _ in range(max_times):
                result = function(*args, **kwargs)
                if result is not None:
                    return result
                time.sleep(sleep_time)
            logging.warning(" [EXIT] %s", args)
            sys.exit(2)
        return wrapped
    return retry_decorator


@retry()
def process_check_result():
    url = NETEYE_URL +  "/v1/actions/process-check-result"
    logging.info("[iC] process_passive_check on url %s", url)

    data = {
            "type": "Service",
            "filter": "host.name==\"{host}\" && service.name==\"{service}\"".format(**args),
            "exit_status":args["exit_status"],
            "plugin_output":args["plugin_output"],
            "check_source":os.uname()[1],
            "pretty":True,
        }

    logging.info("[iC] sending data %s", data)
    r = requests.post(
        url,
        json=data,
        auth=(USER, PW), verify=False,
    )

    logging.info("Got response with status code %d", r.status_code)
    logging.info("Server response was %s", r.text)

    if r.status_code == 200:
        data = r.json()
        if data["results"] == []:
            create_service()
        elif data["results"][0]["status"] == 200:
            logging.info("OK %s", data)
            return data
        elif data["results"][0]["status"] == 500:
            sys.exit(2)
    elif r.status_code == 500:
        sys.exit(2)


@retry()
def create_service():
    url = "{neteye_url}/v1/objects/services/{host}!{service}".format(neteye_url=NETEYE_URL, **args)
    logging.info("[iC] create_service on url %s", url)

    data = {
            "templates":args["service_template"],
            "attrs":{
                "vars.Tornado_Rule":args["rule"],
            }
    }
    logging.info("[iC] sending data %s", data)

    r = requests.put(
        url,
        json=data,
        auth=(USER, PW), verify=False,
    )

    logging.info("Got response with status code %d", r.status_code)
    logging.info("Server response was %s", r.text)

    if r.status_code == 200:
        data = r.json()
        if data["results"] == "":
            create_service()
        elif data["results"][0]["status"] == 200:
            return data
        elif data["resutls"][0]["status"] == 500:
            create_host()
    elif r.status_code == 500:
        create_host()

@retry()
def create_host():
    url = "{neteye_url}/v1/objects/hosts/{host}".format(neteye_url=NETEYE_URL, **args)
    logging.info("[iC] create_service on url %s", url)

    data = {
            "templates":args["host_template"],
            "attrs":{
                "address":"127.0.0.1",
                "check_command":"hostalive",
                "vars.Tornado_Rule":args["rule"],
            }
    }
    logging.info("[iC] sending data %s", data)

    r = requests.put(
        url,
        json=data,
        auth=(USER, PW), verify=False,
    )

    logging.info("Got response with status code %d", r.status_code)
    logging.info("Server response was %s", r.text)

    if r.status_code == 200:
        data = r.json()
        if data["results"][0]["status"] == 200:
            return data
        elif data["resutls"][0]["status"] == 500:
            sys.exit(2)
    elif r.status_code == 500:
        sys.exit(2)

####################################################################################################
# Arguments parsing
####################################################################################################

parser = argparse.ArgumentParser(
    description="Execute Icinga2's process check result and, if needed, create hostname and/or service"
)
parser.add_argument("host", type=str, help="")
parser.add_argument("host_template", type=str, help="")
parser.add_argument("service", type=str, help="")
parser.add_argument("service_template", type=str, help="")
parser.add_argument("plugin_output", type=str, help="")
parser.add_argument("exit_status", type=int, help="")
parser.add_argument("rule", type=str, help="")

args = vars(parser.parse_args())

# Remove eventual spaces and sharps from the service name
args["service"] = re.sub(r"[# ]+", r"_", args["service"])

# Setup the logger
logging.basicConfig(
    filename=LOG_FILE.format(**args),
    level=logging.INFO
)

process_check_result()