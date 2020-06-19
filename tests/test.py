
import requests
from time import sleep, clock
import multiprocessing as mp

def test(index):
    print(f"Start: {index} {clock()}")
    r = requests.put(
        "http://localhost:8000/v1/objects/services/host_test!service_test",
        json={
            "templates":["service_template"],
            "attrs":{},
            "id":index
        },
        auth=("username_test", "password_test"),
        verify=False,
        headers={'Accept': 'application/json',}
    )
    print(f"Stop : {index} {clock()}")


def delayed_iterator(max_n, delay=5e-4):
    print(f"Staring with a delay of {delay} seconds between each request")
    for i in range(max_n):
        sleep(delay)
        yield i

if __name__ == "__main__":
    p = mp.Pool(mp.cpu_count())
    list(p.imap(test, delayed_iterator(10)))