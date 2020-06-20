import json
import fcntl
from threading import Thread
from time import sleep

from ..utils import logger
from .schedule_process_check_result import schedule_process_check_result

class LostPacketsRecoverer(Thread):
    def __init__(self, settings, task_queue, responses_results):
        super(LostPacketsRecoverer, self).__init__()
        self.settings = settings
        self.task_queue = task_queue
        self.responses_results = responses_results
        # Create the file if it doesn't exists yet
        open(settings["lost_packets_path"], "a").close()

    def run(self):
        try:
            while True:
                logger.info("Trying to recover lost packets")
                # Get the packets
                with open(self.settings["lost_packets_path"], "r+") as f:
                    # Acquire the lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    # Read the file
                    messages = f.read()
                    # Delete the content
                    f.truncate(0)
                    # Release the lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN) 
                
                logger.info("Found %d lost packers"%max(len(messages.split("\n")) - 1, 0))

                for line in messages.split("\n"):
                    if line == "":
                        continue
                    try:
                        args = json.loads(line)
                        logger.info("Adding lost packet %s"%args)
                        schedule_process_check_result(args, self.task_queue, self.responses_results)
                    except json.JSONDecodeError:
                        logger.warning("Found a packet which is not a valid Json: %s"%line)

                sleep(self.settings["lost_packet_delay"])
        except KeyboardInterrupt:
            print("Stopped by user")
        