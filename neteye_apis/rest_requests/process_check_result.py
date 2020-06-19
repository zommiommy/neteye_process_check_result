import requests

from ..utils import logger

def process_check_result_request(args):
    url = args["neteye_url"] +  "/v1/actions/process-check-result"

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