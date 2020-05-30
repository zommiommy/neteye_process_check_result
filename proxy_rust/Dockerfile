FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive
# 32 bit
RUN dpkg --add-architecture i386
RUN apt-get update -qyy && apt-get install -qyy apt-utils build-essential software-properties-common
RUN apt-add-repository universe
RUN apt-get update -qyy && apt-get install -qyy \
    curl \
    vim \
    make \
    cmake \
    gcc \
    g++ \
    flex \
    bison \
    pkg-config \
    openssl \
    libssl-dev

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /root/rustup.sh
RUN chmod +x /root/rustup.sh
RUN /root/rustup.sh --default-host x86_64-unknown-linux-gnu --default-toolchain nightly --profile default -y
RUN echo "source /root/.cargo/env" >> /root/.bashrc

WORKDIR /home
CMD cargo build --release