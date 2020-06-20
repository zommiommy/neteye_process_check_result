import logging
import requests

from time import sleep

from .logger import logger

def retry(max_times=5, sleep_time=3):
    def retry_decorator(function):
        def wrapped(*args, **kwargs):
            for _ in range(max_times):
                try:
                    result = function(*args, **kwargs)
                    if result is not None:
                        return result
                except requests.exceptions.Timeout:
                    logging.warning("The function %s went in timeout", function.__name__)
                sleep(sleep_time)
            text = " [EXIT] %s reached max number of tries from the arguments %s", function.__name__, args
            logging.warning(text)
            return 500, text, text
        return wrapped
    return retry_decorator