

def filter_args(args):
    return {
        key: args[key]
        for key in [
            "host",
            "host_template",
            "service",
            "service_template",
            "plugin_output",
            "exit_status",
            "eventid",
            "check_source",
            "client_id"
        ]
    }