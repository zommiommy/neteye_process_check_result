import sys

from .settings import get_settings
from .utils import is_proxy_up as is_proxy_up_inner

def is_proxy_up():
    settings = get_settings(get_auth=False)
    result =  is_proxy_up_inner(
            settings["proxy_ip"],
            settings["proxy_port"]
        )

    if result:
        print("yes")
    else:
        print("no")

    sys.exit(1 - int(result))