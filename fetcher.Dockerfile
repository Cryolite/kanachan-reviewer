FROM ubuntu:latest

RUN apt-get update && apt-get -y dist-upgrade && apt-get -y install \
      ca-certificates \
      fonts-ipafont \
      fonts-ipaexfont \
      libnss3-tools \
      protobuf-compiler \
      python3-pip \
      unzip \
      wget && \
    wget -q -O - 'https://dl-ssl.google.com/linux/linux_signing_key.pub' | apt-key add - && \
    echo 'deb http://dl.google.com/linux/chrome/deb/ stable main' >> /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    python3 -m pip install -U pip && \
    wget "https://chromedriver.storage.googleapis.com/`wget -O - https://chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip" && \
    unzip chromedriver_linux64.zip -d /usr/local/bin && \
    rm chromedriver_linux64.zip && \
    mkdir /opt/kanachan-reviewer && \
    useradd -ms /bin/bash ubuntu

COPY . /opt/kanachan-reviewer/

WORKDIR /opt/kanachan-reviewer

RUN protoc --python_out=. kanachan_reviewer/mahjongsoul.proto && \
    python3 -m pip install -U .

USER ubuntu

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION python

ENTRYPOINT ["/opt/kanachan-reviewer/launch-fetcher.sh"]
