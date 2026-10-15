# jpeg-ultra-scan-c
naive c port of [jpegultrascan](https://github.com/MegaByte/jpegultrascan/).

## status:

* output parity.

* multi-threaded.

## usage:
```
$ ./jpeg-ultra-scan-c --help
Usage: ./jpeg-ultra-scan-c [options] <infile.jpg> <outfile.jpg>
Options:
  -mode [seq|extseq|prog|brute|smart]
  -copy [none|all]              Metadata retention (default: none)
  -b <splits>                   Number of spectral bit splits
  -d <interleave>               DC component interleaving (0 or 1)
  -allowarith                   Allow arithmetic encoding if it optimizes output footprint
  -noarith                      Force absolute Huffman decoding compliance across all files
  -q                            Quiet mode
  -s<N>                         Strip APP markers (N from 0 to 15)
```

## stats:
```
$ python3 test_harness.py
Running pythonized multi-image benchmarking harness (in SIMD)...

Pipeline Target | Profile Properties     | Size     | Runtime  | Delta / Status
====================================================================================
[IMG_20260924_133231.jpg]
  Original      | 2485x1248 Baseline (8b) | 3553491  | -        | REF
  Perl          | 2485x1248 Prog-Huff (8b) | 3061284  | 1728.336s | -492207 (WIN)
  C Baseline    | 2485x1248 Baseline (8b) | 3219682  | 0.139s   | -333809 (WIN)
  C Ext-Seq     | 2485x1248 Baseline (8b) | 3219700  | 0.139s   | -333791 (WIN)
  C Prog-Stripped | 2485x1248 Prog-Huff (8b) | 3061284  | 325.920s | -492207 (WIN)
  C Prog-Parity | 2485x1248 Prog-Huff (8b) | 3061284  | 328.283s | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[baboon.jpg]
  Original      | 512x512 Baseline (8b)  | 56938    | -        | REF
  Perl          | 512x512 Prog-Huff (8b) | 51746    | 103.230s | -5192 (WIN)
  C Baseline    | 512x512 Baseline (8b)  | 52949    | 0.004s   | -3989 (WIN)
  C Ext-Seq     | 512x512 Baseline (8b)  | 52967    | 0.004s   | -3971 (WIN)
  C Prog-Stripped | 512x512 Prog-Huff (8b) | 51288    | 9.576s   | -5650 (WIN 🔥)
  C Prog-Parity | 512x512 Prog-Huff (8b) | 51746    | 9.697s   | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[monkey12.jpg]
  Original      | 149x227 Ext-Seq (12b)  | 32831    | -        | REF
  Perl          | 149x227 Prog-Huff (12b) | 30922    | 71.4218s | -1909 (WIN)
  C Baseline    | 149x227 Ext-Seq (12b)  | 29771    | 0.002s   | -3060 (WIN 🔥)
  C Ext-Seq     | 149x227 Ext-Seq (12b)  | 29789    | 0.002s   | -3042 (WIN 🔥)
  C Prog-Stripped | 149x227 Ext-Seq (12b)  | 29771    | 0.003s   | -3060 (WIN 🔥)
  C Prog-Parity | 149x227 Ext-Seq (12b)  | 32813    | 0.002s   | -18 (WIN)
------------------------------------------------------------------------------------
[testimgari.jpg]
  Original      | 227x149 Ext-Seq (8b)   | 5126     | -        | REF
  Perl          | 227x149 Ext-Seq (8b)   | 5126     | 62.965s  | 0 (PARITY)
  C Baseline    | 227x149 Ext-Seq (8b)   | 5108     | 0.003s   | -18 (WIN 🔥)
  C Ext-Seq     | 227x149 Ext-Seq (8b)   | 5126     | 0.003s   | 0 (PARITY)
  C Prog-Stripped | 227x149 Progressive DCT, arithmetic coding (8b) | 5129     | 0.003s   | +3 (PROG)
  C Prog-Parity | 227x149 Progressive DCT, arithmetic coding (8b) | 5129     | 0.003s   | +3 (PROG)
------------------------------------------------------------------------------------
[testimgint.jpg]
  Original      | 227x149 Baseline (8b)  | 5756     | -        | REF
  Perl          | 227x149 Prog-Huff (8b) | 5437     | 62.1008s | -319 (WIN)
  C Baseline    | 227x149 Baseline (8b)  | 5441     | 0.001s   | -315 (WIN)
  C Ext-Seq     | 227x149 Baseline (8b)  | 5459     | 0.001s   | -297 (WIN)
  C Prog-Stripped | 227x149 Prog-Huff (8b) | 5437     | 1.974s   | -319 (WIN)
  C Prog-Parity | 227x149 Prog-Huff (8b) | 5437     | 1.962s   | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[testorig.jpg]
  Original      | 227x149 Baseline (8b)  | 5770     | -        | REF
  Perl          | 227x149 Prog-Huff (8b) | 5452     | 62.311s  | -318 (WIN)
  C Baseline    | 227x149 Baseline (8b)  | 5445     | 0.001s   | -325 (WIN 🔥)
  C Ext-Seq     | 227x149 Baseline (8b)  | 5463     | 0.002s   | -307 (WIN)
  C Prog-Stripped | 227x149 Prog-Huff (8b) | 5452     | 1.945s   | -318 (WIN)
  C Prog-Parity | 227x149 Prog-Huff (8b) | 5452     | 1.929s   | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
```
