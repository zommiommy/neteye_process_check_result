import fcntl
import logging
from base64 import urlsafe_b64encode

def lock(path):
    """I have already checked, the unlock works even if the subfunction exits with sys.exit"""
    def lock_internal(function):
        def wrapped(args):
            args["hostb64"] = urlsafe_b64encode(args["host"].encode())
            args["serviceb64"] = urlsafe_b64encode(args["service"].encode())
            lock_path = path.format(**args)
            with open(lock_path, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                result = function(args)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN) 
                return result
        return wrapped
    return lock_internal