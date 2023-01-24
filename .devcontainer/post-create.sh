#!/usr/bin/env bash

set -euxo pipefail

# Install prerequisite packages.
sudo apt-get update
sudo apt-get -y dist-upgrade
sudo apt-get -y install \
  protobuf-compiler

# Install CUDA 11.7.1. See https://docs.nvidia.com/cuda/wsl-user-guide/index.html#getting-started-with-cuda-on-wsl.
pushd ~
wget 'https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin'
sudo mv cuda-wsl-ubuntu.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget 'https://developer.download.nvidia.com/compute/cuda/11.7.1/local_installers/cuda-repo-wsl-ubuntu-11-7-local_11.7.1-1_amd64.deb'
sudo dpkg -i cuda-repo-wsl-ubuntu-11-7-local_11.7.1-1_amd64.deb
rm -f cuda-repo-wsl-ubuntu-11-7-local_11.7.1-1_amd64.deb
popd
sudo cp /var/cuda-repo-wsl-ubuntu-11-7-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

pushd /workspaces/kanachan-reviewer
# See https://github.com/microsoft/pylance-release/issues/351.
python3 -m pip install -U mypy-protobuf
protoc --python_out=. --mypy_out=. kanachan_reviewer/mahjongsoul.proto
popd

# Install PyTorch and other prerequisite Python packages.
python3 -m pip install -U pip setuptools wheel
python3 -m pip install -U /workspaces/kanachan-reviewer
