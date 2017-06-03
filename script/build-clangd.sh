#!/usr/bin/env bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

die() {
    echo $1
    exit -1
}

fetch_src() {
    if [ ! -d llvm-src ]; then
        git clone --depth=1 https://github.com/llvm-mirror/llvm llvm-src
    else
        echo 'Use existing llvm-src'
    fi
    if [ ! -d llvm-src/tools/clang ]; then
        git clone --depth=1 https://github.com/llvm-mirror/clang llvm-src/tools/clang
    else
        echo 'Use existing llvm-src/tools/clang'
    fi

    if [ ! -d llvm-src/tools/clang/tools/extra ]; then
        git clone --depth=1 https://github.com/llvm-mirror/clang-tools-extra llvm-src/tools/clang/tools/extra
    else
        echo 'Use existing llvm-src/tools/clang/tools/extra'
    fi
}

check_prerequiresite() {
    HAS_MAKE="$(which make || :)"
    HAS_CMAKE="$(which cmake || :)"
    if [ -z "$HAS_MAKE" ]; then
        die "failed to find make, are you have develop tools installed? "
    fi
    if [ -z "$HAS_CMAKE" ]; then
        die "failed to find cmake, are you have develop tools installed? "
    fi

    if [ "$(uname -s)" == "Darwin" ]; then
        HAS_COMPILER="$(which clang || :)"
        HAS_CXX_COMPILER="$(which clang++ || :)"
    else
        HAS_COMPILER="$(which gcc || :)"
        HAS_CXX_COMPILER="$(which g++ || :)"
    fi

    if [ -z "$HAS_COMPILER" ]; then
        die "failed to find c compiler, are you have develop tools installed? "
    fi
    if [ -z "$HAS_CXX_COMPILER" ]; then
        die "failed to find c++ compiler, are you have develop tools installed? "
    fi

    HAS_CLANG="$(which clang || :)"
    # prefer to clang if found
    if [ -z "$CC" ]; then
        if [ -z "$HAS_CLANG" ]; then
            CC=gcc
        else
            CC=clang
        fi
    fi

    # prefer to clang if found
    if [ -z "$CXX" ]; then
        if [ -z "$HAS_CLANG" ]; then
            CXX=g++
        else
            CXX=clang++
        fi
    fi

    if [ ! -z "$(which ninja || :)" -o ! -z "$(which ninja-build || :)" ]; then
        CMAKE_ARGS="$CMAKE_ARGS -G Ninja"
        echo 'Using Ninja Generators'
    else
        CMAKE_ARGS="$CMAKE_ARGS"
    fi
}

build_clangd() {
    mkdir -p build-llvm
    pushd build-llvm
    cmake $CMAKE_ARGS \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=$CC \
        -DCMAKE_CXX_COMPILER=$CXX \
        ../llvm-src
    ninja clangd
    popd
}

post_build() {
    cp build-llvm/bin/clangd clangd
    echo "clangd is built at $PWD/clangd"
}

fetch_src
check_prerequiresite
build_clangd
post_build

