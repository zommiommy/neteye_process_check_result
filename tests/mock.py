import os
import re
import sys
import json
from time import sleep
import requests
from flask import Flask, request, jsonify
from pprint import pprint
from multiprocessing import Manager, Queue
from threading import Thread
from uuid import uuid4

####################################################################################################
# Globals
####################################################################################################
app = Flask(__name__)
manager = Manager()
responses_results = manager.dict()
queue = Queue()

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.abspath(__file__)))

####################################################################################################
# Routes
####################################################################################################

@app.route('/v1/objects/hosts/<host>', methods=["PUT"])
def create_host(host):
    sleep(1)
    return jsonify({"results":["paragasessa"]})

@app.route('/v1/objects/services/<host>!<service>', methods=["PUT"])
def create_service(host, service):
    sleep(1)
    return jsonify({"results":["paragasessa"]})

@app.route('/v1/objects/services/<host>!<service>', methods=["GET"])
def check_service(host, service):
    sleep(1)
    return jsonify({"results":["paragasessa"]})

@app.route('/v1/actions/process-check-result', methods=["POST"])
def process_check_result():
    sleep(1)
    return jsonify({"results":["paragasessa"]})


if __name__ == "__main__":
    app.run(host = '0.0.0.0', port = 8888)