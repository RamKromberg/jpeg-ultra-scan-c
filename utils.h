#ifndef UTILS_H
#define UTILS_H

/* clang-format off */
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <jpeglib.h>
/* clang-format on */

#define MAX_COEF 63
#define MAX_PLANES 4
#define MAX_BITS_LIMIT 14
#define CHANNEL_CAPACITY 65536

typedef enum {
	MODE_BASELINE_SEQ, /* Pure single-scan baseline sequential (-mode seq) */
	MODE_EXTENDED_SEQ, /* Multi-scan spectral split sequential (-mode extseq) */
	MODE_PROGRESSIVE, /* Multi-scan bit progressive split (-mode prog) */
	MODE_BRUTE, /* Run full pipeline comparison pass, select minimum */
	MODE_SMART /* Predictive metadata placeholder boundary */
} run_mode_t;

typedef enum {
	COPY_NONE, /* Strip all extra metadata markers (-copy none) */
	COPY_ALL /* Retain all source APP and COM markers (-copy all) */
} copy_mode_t;

extern run_mode_t flag_run_mode;
extern copy_mode_t flag_copy_mode; // NEW: Track header replication state
extern bool flag_verbose;
extern bool flag_quiet;
extern int flag_bit_splits;
extern int flag_dc_interleave;
extern char* flag_strip_mode;
extern bool flag_arithmetic;
extern bool flag_allow_arithmetic; // Explicitly allow arithmetic conversion if smaller (-allowarith)
extern bool flag_force_no_arithmetic; // Global killswitch forcing Huffman output (-noarith)
extern bool flag_strip_app[16];

extern size_t dp_ac_sizes[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern size_t dp_dc_sizes[MAX_PLANES][MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern size_t dp_dc_interleaved_sizes[MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern size_t dp_ac_best_size[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1];
extern int dp_ac_best_split[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1];
extern int dp_ac_best_bits[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1];
extern int dp_ac_best_depth[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1];

/* Expanded 5-Dimensional Decision Trees to Track High-Order Ah Splits */
extern size_t dp_ac_bit_best_size[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern int dp_ac_bit_best_split[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern int dp_ac_bit_best_depth[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT];
extern bool dp_ac_bit_computed[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT];

/* Reset the dynamic cache tracking declarations */
void clear_optimization_caches(void);
int solve_perl_progressive_scans(jpeg_scan_info* target, int plane, int a, int b, int flag_max_b);

void print_usage(const char* prog);
bool parse_command_line(int argc, char** argv, char** infile, char** outfile);
void configure_metadata_copy_pipeline(j_compress_ptr cinfo, j_decompress_ptr dinfo);
size_t extract_target_scan_size(const unsigned char* buf_ptr, unsigned long total_len, int target_scan_idx);
int compare_scans_parity(const void* a, const void* b);
void sort_scans_topologically(jpeg_scan_info* scans, int num_scans);

void audit_binary_structure(const unsigned char* buf, size_t size);

#endif
