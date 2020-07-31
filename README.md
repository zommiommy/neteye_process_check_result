# neteye_process_check_result

Execute Icinga2's process check result and, if needed, create hostname and/or service

```
./neteye_process_check_result -h
usage: -c [-h] host host_template service service_template plugin_output exit_status log_file eventid

Execute Icinga2's process check result and, if needed, create hostname and/or service

positional arguments:
  host
  host_template
  service
  service_template
  plugin_output
  exit_status
  log_file          The name of the log that will be created
  eventid           A progressive identifier that's used to order the requests

optional arguments:
  -h, --help        show this help message and exit
```

Example:
```bash
./neteye_process_check_result HOST HOST_TEMPLATE SERVICE SERVICE_TEMPLATE PLUGIN_OUTPUT 1 LOG_FILE.log 10
```

## Proxy
The proxy can be started with:
```bash
./start_proxy
```

And you can check if the proxy is still up with:
```bash
./is_proxy_up
```

All its settings are in `settings.json`:
```json
{
    "neteye_url":"https://neteye.api:8080",
    "proxy_ip":"127.0.0.1",
    "proxy_port":9966,
    "user":"director",
    "pw_file":"/root/super_safe_file.txt",
    "pw_regex":"password *= *\"(.+)\"",
    "log_path":"/var/log/proxy.log",
    "fork_proxy":true,
    "proxy_fork_delay":0.5,
    "lost_packet_delay":60,
    "lost_packets_path":"/var/log/neteye_process_check_result_lost_packets.txt"
}
```
- neteye_url : the url to the neteye's apis
- proxy_ip : binding ip of the proxy, 127.0.0.1 to listen to local host only, 0.0.0.0 if open to all.
- proxy_port : the binding port of the proxy
- user : user to authenticate to neteye's apis
- pw_file : the file to read to extract the password to authenticate to neteye's apis
- pw_regex : the regex to extract the password from the content of `pw_file`.
- log_path : Where to log
- fork_proxy : If enabled, the proxy will fork into a second process. This allows the proxy to automatically restart if the proxy crashes.
- proxy_fork_delay : How much time the proxy will wait before restarting itself.
- lost_packet_delay  : Every `lost_packet_delay` seconds the proxy will check if the logs file contains any lost packets from previous executions that have to be sent to neteye.
- lost_packets_path : Where to save the lost packets

# Flowchart

This is the flow chart which tries to explain the relation between the client and the proxy.

![](https://github.com/zommiommy/neteye_process_check_result/raw/master/flowchart.jpg)
