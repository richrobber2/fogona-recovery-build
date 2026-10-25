#!/bin/sh
set -eu
include_dir=$1
build_dir=$2
compiler=${CXX:-clang++}
mkdir -p "$build_dir"
"$compiler" -std=c++17 -Wall -Wextra -Werror -I "$include_dir" -Dmain=fogona_probe_main \
    -c device/crypto/check-keymint.cpp -o "$build_dir/keymint-probe.o"
"$compiler" -std=c++17 -Wall -Wextra -Werror tests/keymint_probe_test.cpp "$build_dir/keymint-probe.o" \
    -Wl,--wrap=dlopen -Wl,--wrap=dlsym -Wl,--wrap=dlclose -Wl,--wrap=dlerror -ldl -o "$build_dir/keymint-probe-test"
"$build_dir/keymint-probe-test"
