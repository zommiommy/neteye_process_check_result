from threading import Thread
from time import sleep

from ..apis import process_check_result
from ..utils import logger

class RequestsExecutor(Thread):

    def __init__(self, queue, responses_results):
        super(RequestsExecutor, self).__init__()
        self.queue = queue
        self.responses_results = responses_results
        self.tasks = []
    
    def _recv_tasks(self):
        while not self.queue.empty() or self.tasks == []:
            self.tasks.append(self.queue.get())
            if len(self.tasks) < 5:
                sleep(0.3)
        self.tasks.sort()


    def run(self):
        try:
            while True:
                self._recv_tasks()

                priority_id, task = self.tasks.pop(0)
                _id = task["id"]
                logger.info("Executing task of the client %s"%task["client_id"])
                logger.debug("Executing task %s"%task)
                
                try:
                    text = process_check_result(task, recovery=True)
                    data = {
                        "status_code": 200 if text is not None else 500,
                        "content":text if text is not None else "Error"
                    }
                except Exception as e:
                    data = {
                        "status_code": 500,
                        "content":"The proxy had the following error when trying to do the process_check_result [%s]"%str(e)
                    }

                self.responses_results[_id] = data
        except KeyboardInterrupt:
            print("Stopped by user")
