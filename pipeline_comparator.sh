#!/bin/sh

# Clean out old state logs to prevent stale cross-examination
#rm -f ./.cache_comparator_perl/*.log

mkdir -p ./.cache_comparator_perl

if [ ! -f ./.cache_comparator_perl/baboon.jpg.perl_trace.log ]; then
    perl ./jpegultrascan/jpegultrascan.pl --trace ./test_images/baboon.jpg ./.cache_comparator_perl/baboon.jpg.perl_out.jpg > ./.cache_comparator_perl/baboon.jpg.perl_trace.log
fi

python ./pipeline_comparator.py ./test_images/baboon.jpg --binary ./jpeg-ultra-scan-c_debug
