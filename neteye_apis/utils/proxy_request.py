import requests

try:
    from time import clock
    timestamp_funciton = clock
except ImportError:
    from time import perf_counter_ns
    timestamp_funciton = perf_counter_ns

def proxy_request(args):
    args["epoch"] = timestamp_funciton()
    args["priority_id"] = args["event_id"]
    
    r = requests.post(
        args["proxy_url"],
        json=args, verify=False,
        headers={
            "Accept": "application/json"
        }
    )
    return r.status_code, r.text
