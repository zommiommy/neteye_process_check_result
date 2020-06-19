import os
import re
import sys
import json

def get_settings():
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "settings.json"
        )
    )

    with open(path, "r") as f:
        settings = json.load(f)

    settings["proxy_url"] = """http://{proxy_ip}:{proxy_port}""".format(**settings) # MUST be http

    with open(settings["pw_file"]) as f:
        match = re.search(settings["pw_regex"], f.read())
        if match:
            settings["pw"] = match.group(1)
        else:
            print("CANNOT FIND PASSWORD")
            sys.exit(-1)
    return settings