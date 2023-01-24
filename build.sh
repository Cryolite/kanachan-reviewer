#!/usr/bin/env bash

set -euxo pipefail

sudo chown -R ubuntu:ubuntu /var/log/kanachan-reviewer
sudo rm -rf /srv/kanachan-reviewer/*
sudo chown ubuntu:ubuntu /srv/kanachan-reviewer
#pushd monitor
#yes 'y' | npm init vue@latest vue || true
#cp vue_/src/* vue/src
#cp vue_/index.html vue
#pushd vue
#npm install
#npm run build
#mv dist /srv/mahjongsoul-sniffer/game-detail-crawler
#popd
#popd
