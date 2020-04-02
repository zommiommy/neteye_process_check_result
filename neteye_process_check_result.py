#!/bin/python
import os
import re
import sys
import uuid
import time
import urllib
import logging
import requests
import argparse
####################################################################################################
# Constants
####################################################################################################
NETEYE_URL = """https://100.67.0.25:5665"""
USER="director"

PW_FILE="/neteye/shared/icinga2/conf/icinga2/conf.d/director-user.conf"
with open(PW_FILE) as f:
    match = re.search(r"password *= *\"(.+)\"", f.read())
    if match:
        PW = match.group(1)
    else:
        print("CANNOT FIND PASSWORD")
        sys.exit(-1)


LOG_FILE = """/neteye/shared/tornado/data/archive/all/tornado_{rule}_creation.log"""
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
            logging.warning(" [EXIT] %s reached max number of tries from the arguments %s", function.__name__, args)
            sys.exit(2)
        return wrapped
    return retry_decorator


@retry()
def process_check_result():
    url = NETEYE_URL +  "/v1/actions/process-check-result"
    logging.info("[PC] process_check_result on url %s", url)

    data = {
            "type": "Service",
            "filter": "host.name==\"{host}\" && service.name==\"{service}\"".format(**args),
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


    if r.status_code == 200:
        data = r.json()
        if data["results"] == []:
            logging.info("[PC] KO : %s", data)
            create_service()
        else:
            logging.info("[PC] OK : %s", data)
            return data

    logging.warning("[PC] Error : %s", r.text.replace("\n", ""))
    if r.status_code in [500, 503]:
        create_service()


@retry()
def create_service():
    url = "{neteye_url}/v1/objects/services/{host}!{service}".format(
        neteye_url=NETEYE_URL,
        host=urllib.quote(args["host"]).replace("/", "%2F"),
        service=urllib.quote(args["service"]).replace("/", "%2F"),
    )
    logging.info("[SC] creating service on url %s", url)

    data = {
            "templates":[args["service_template"]],
            "attrs":{
                "vars.Tornado_Rule":args["rule"],
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

    if r.status_code == 200:
        logging.info("[SC] OK : %s", r.json())
        return r.json()
    
    logging.warning("[SC] Error : %s", r.text.replace("\n", ""))
    if r.status_code in [500, 503]:
        create_host()

@retry()
def create_host():
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
                "vars.Tornado_Rule":args["rule"],
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

    if r.status_code == 200:
        logging.info("[HC] OK : %s", r.json())
        return r.json()
    elif r.status_code in [500, 503]:
        logging.warning("[HC] got error: %s", r.json()["errors"])
        sys.exit(2)

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
    parser.add_argument("rule", type=str, help="")

    args = vars(parser.parse_args())

    # Setup the logger
    FORMAT = "{uuid} %(levelname)s %(asctime)-15s %(message)s".format(uuid=uuid.uuid4())
    logging.basicConfig(
        filename=LOG_FILE.format(**args),
        level=logging.INFO,
        format=FORMAT
    )

    logging.info("START")
    data = process_check_result()
    logging.info("OK : %s", data["results"])
    logging.info("STOP")