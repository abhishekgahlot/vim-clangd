#!/usr/bin/env bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

docker build -t clangd:ubuntu-16.04 -f Dockerfile.xenial .
docker run -it -v $PWD/../script:/build -w /build clangd:ubuntu-16.04 ./build-clangd.sh
cp -v ../script/clangd{,-ubuntu-16.04}
