import requests

from ..utils import logger

def create_host_request(args):
    url = "{neteye_url}/v1/objects/hosts/{host}".format(
        neteye_url=args["neteye_url"],
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