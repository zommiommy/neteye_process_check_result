
from uuid import uuid4
from time import sleep

def schedule_process_check_result(params, task_queue, responses_results):
    _id = uuid4().hex
    params["id"] = _id

    task_queue.put((params.pop("epoch"), params))

    while _id not in responses_results:
        sleep(0.1)

    response = responses_results.pop(_id)
    return response["content"], response["status_code"]
    