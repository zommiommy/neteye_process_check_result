import requests

from ..utils import logger

def create_service_request(args):
    url = "{neteye_url}/v1/objects/services/{host}!{service}".format(
        neteye_url=args["neteye_url"],
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