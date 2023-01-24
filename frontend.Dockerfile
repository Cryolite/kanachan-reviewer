FROM ubuntu:latest

RUN apt-get update && apt-get -y dist-upgrade && apt-get -y install \
      protobuf-compiler \
      python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install -U pip && \
    mkdir /opt/kanachan-reviewer && \
    useradd -ms /bin/bash ubuntu

COPY . /opt/kanachan-reviewer/

WORKDIR /opt/kanachan-reviewer

RUN protoc --python_out=. kanachan_reviewer/mahjongsoul.proto && \
    python3 -m pip install -U .

USER ubuntu

ENV FLASK_APP /opt/kanachan-reviewer/frontend.py

ENTRYPOINT ["flask", "run", "--host=0.0.0.0"]
