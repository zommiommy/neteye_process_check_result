import requests
from .filter_args import filter_args

try:
    from time import clock
    timestamp_funciton = clock
except ImportError:
    from time import perf_counter_ns
    timestamp_funciton = perf_counter_ns

def proxy_request(args):
    args["epoch"] = timestamp_funciton()

    r = requests.post(
        args["proxy_url"],
        json=filter_args(args), verify=False,
        headers={
            "Accept": "application/json"
        }
    )
    return r.status_code, r.text
