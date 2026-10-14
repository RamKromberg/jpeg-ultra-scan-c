#!/bin/sh

make clean

CFLAGS=$(pkg-config --cflags libjpeg)
LDFLAGS=$(pkg-config --libs libjpeg)

gcc -Wall -Wextra -g -O0 -std=c11 -DDIAGNOSTIC_TRACE $CFLAGS main.c utils.c -o jpeg-ultra-scan-c $LDFLAGS

echo "=== STARTING VALGRIND EMULATION METRIC SWEEP ==="
time valgrind --tool=memcheck \
         --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --verbose \
         ./jpeg-ultra-scan-c -mode prog -q ./test_images/baboon.jpg ./output_c.jpg > c_script.log 2>&1

echo "=== VALGRIND EXECUTION PASS COMPLETE ==="
