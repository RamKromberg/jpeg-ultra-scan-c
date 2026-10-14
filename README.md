# jpeg-ultra-scan-c
naive c port of [jpegultrascan](https://github.com/MegaByte/jpegultrascan/)

## status:

in output parity.

not optimized for now.

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
$ make test
gcc -O3 -std=c11 -I/nix/store/4q13ynbk8q4w753fldqakkrh67v9c782-libjpeg-turbo-3.1.4-dev/include -c main.c -o main.o
gcc -O3 -std=c11 -I/nix/store/4q13ynbk8q4w753fldqakkrh67v9c782-libjpeg-turbo-3.1.4-dev/include -c utils.c -o utils.o
gcc -O3 -std=c11 -I/nix/store/4q13ynbk8q4w753fldqakkrh67v9c782-libjpeg-turbo-3.1.4-dev/include -o jpeg-ultra-scan-c main.o utils.o -L/nix/store/4b02z88l6q821j6xx1449k8kx3igd4mh-libjpeg-turbo-3.1.4/lib -ljpeg
python3 test_harness.py
Running pythonized multi-image benchmarking harness (in SIMD)...

Pipeline Target | Profile Properties     | Size     | Runtime  | Delta / Status
====================================================================================
[IMG_20260924_133231.jpg]
  Original      | 2485x1248 Baseline (8b) | 3553491  | -        | REF           
  Perl          | 2485x1248 Prog-Huff (8b) | 3061284  | 1728.336s | -492207 (WIN) 
  C Baseline    | 2485x1248 Baseline (8b) | 3219682  | 0.136s   | -333809 (WIN) 
  C Ext-Seq     | 2485x1248 Baseline (8b) | 3219700  | 0.135s   | -333791 (WIN) 
  C Prog-Stripped | 2485x1248 Prog-Huff (8b) | 3061284  | 1052.261s | -492207 (WIN) 
  C Prog-Parity | 2485x1248 Prog-Huff (8b) | 3061284  | 1053.117s | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[baboon.jpg]
  Original      | 512x512 Baseline (8b)  | 56938    | -        | REF           
  Perl          | 512x512 Prog-Huff (8b) | 51746    | 100.413s | -5192 (WIN)   
  C Baseline    | 512x512 Baseline (8b)  | 52949    | 0.004s   | -3989 (WIN)   
  C Ext-Seq     | 512x512 Baseline (8b)  | 52967    | 0.005s   | -3971 (WIN)   
  C Prog-Stripped | 512x512 Prog-Huff (8b) | 51288    | 27.536s  | -5650 (WIN 🔥) 
  C Prog-Parity | 512x512 Prog-Huff (8b) | 51746    | 27.518s  | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[monkey12.jpg]
  Original      | 149x227 Ext-Seq (12b)  | 32831    | -        | REF           
  Perl          | 149x227 Prog-Huff (12b) | 30922    | 71.4218s | -1909 (WIN)   
  C Baseline    | 149x227 Ext-Seq (12b)  | 29771    | 0.002s   | -3060 (WIN 🔥) 
  C Ext-Seq     | 149x227 Ext-Seq (12b)  | 29789    | 0.003s   | -3042 (WIN 🔥) 
  C Prog-Stripped | 149x227 Ext-Seq (12b)  | 29771    | 0.003s   | -3060 (WIN 🔥) 
  C Prog-Parity | 149x227 Ext-Seq (12b)  | 32813    | 0.003s   | -18 (WIN)     
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
  C Ext-Seq     | 227x149 Baseline (8b)  | 5459     | 0.002s   | -297 (WIN)    
  C Prog-Stripped | 227x149 Prog-Huff (8b) | 5437     | 4.427s   | -319 (WIN)    
  C Prog-Parity | 227x149 Prog-Huff (8b) | 5437     | 4.413s   | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
[testorig.jpg]
  Original      | 227x149 Baseline (8b)  | 5770     | -        | REF           
  Perl          | 227x149 Prog-Huff (8b) | 5452     | 62.311s  | -318 (WIN)    
  C Baseline    | 227x149 Baseline (8b)  | 5445     | 0.001s   | -325 (WIN 🔥)  
  C Ext-Seq     | 227x149 Baseline (8b)  | 5463     | 0.001s   | -307 (WIN)    
  C Prog-Stripped | 227x149 Prog-Huff (8b) | 5452     | 4.422s   | -318 (WIN)    
  C Prog-Parity | 227x149 Prog-Huff (8b) | 5452     | 4.430s   | 🔥 BIT PARITY 🔥
------------------------------------------------------------------------------------
```
