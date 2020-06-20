from threading import Thread
from multiprocessing import Queue

from .requests_executor import RequestsExecutor


class ExecutorsCreator(Thread):
    def __init__(self, settings, task_queue, responses_results):
        super(ExecutorsCreator, self).__init__()
        self.settings = settings
        self.task_queue = task_queue
        self.responses_results = responses_results

    def _setup_queue(self, lock, tasks):
        if lock not in tasks:
            _queue = Queue()
            tasks[lock] = _queue
            RequestsExecutor(self.settings, _queue, self.responses_results).start()

    def run(self):
        tasks = {}
        try:
            while True:
                epoch, task = self.task_queue.get()
                lock = (task["service"], task["host"])
                self._setup_queue(lock, tasks)
                tasks[lock].put((epoch, task))
        except KeyboardInterrupt:
            print("Stopped by user")
        