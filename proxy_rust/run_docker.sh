#!/bin/bash
sudo docker build -t rust-devel .
sudo docker run -it --net=host -v "$PWD/proxy_rust:/home" rust-devel bash