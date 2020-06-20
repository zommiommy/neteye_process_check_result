import requests

try:
    from time import clock
    timestamp_funciton = clock
except ImportError:
    from time import perf_counter_ns
    timestamp_funciton = perf_counter_ns

def proxy_request(args):
    args["epoch"] = timestamp_funciton()

    data = {
        key: args[key]
        for key in [
            "host",
            "host_template",
            "service",
            "service_template",
            "plugin_output",
            "exit_status",
            "eventid",
            "client_id"
        ]
    }

    r = requests.post(
        args["proxy_url"],
        json=data, verify=False,
        headers={
            "Accept": "application/json"
        }
    )
    return r.status_code, r.text
