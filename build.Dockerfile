FROM ubuntu:latest

RUN apt-get update && apt-get -y dist-upgrade && apt-get -y install \
      curl \
      protobuf-compiler \
      python3-pip \
      sudo && \
    curl -fsSL 'https://deb.nodesource.com/setup_lts.x' | bash - && \
    apt-get update && apt-get -y install \
      nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    npm install --location=global npm@latest && \
    npm init vue@latest && \
    mkdir /opt/kanachan-reviewer && \
    useradd -ms /bin/bash ubuntu && \
    usermod -aG sudo ubuntu && \
    newgrp sudo && \
    echo '%sudo ALL=(ALL:ALL) NOPASSWD:ALL' >> /etc/sudoers

COPY . /opt/kanachan-reviewer/

WORKDIR /opt/kanachan-reviewer

RUN protoc --python_out=. kanachan_reviewer/mahjongsoul.proto && \
    python3 -m pip install -U .

USER ubuntu

ENTRYPOINT ["bash", "/opt/kanachan-reviewer/build.sh"]
