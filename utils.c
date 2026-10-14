#include "utils.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

size_t dp_ac_sizes[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
size_t dp_dc_sizes[MAX_PLANES][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
size_t dp_dc_interleaved_sizes[MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
size_t dp_ac_best_size[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1] = { 0 };
int dp_ac_best_split[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1] = { 0 };
int dp_ac_best_bits[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1] = { 0 };
int dp_ac_best_depth[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1] = { 0 };

/* Realized 5-Dimensional Decision Trees Storage Blocks */
size_t dp_ac_bit_best_size[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
int dp_ac_bit_best_split[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
int dp_ac_bit_best_depth[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { 0 };
bool dp_ac_bit_computed[MAX_PLANES][MAX_COEF + 1][MAX_COEF + 1][MAX_BITS_LIMIT][MAX_BITS_LIMIT] = { false };

run_mode_t flag_run_mode = MODE_EXTENDED_SEQ;
copy_mode_t flag_copy_mode = COPY_NONE; // Default to optimized stripped files
bool flag_arithmetic = false;
bool flag_allow_arithmetic = false;
bool flag_force_no_arithmetic = false;
int flag_bit_splits = 3; // Align with Perl's default $maxbits = 3
int flag_dc_interleave = 0;
bool flag_quiet = false;
bool flag_strip_app[16] = { false };

void print_usage(const char* prog) {
	fprintf(stderr, "Usage: %s [options] <infile.jpg> <outfile.jpg>\n", prog);
	fprintf(stderr, "Options:\n");
	fprintf(stderr, "  -mode [seq|extseq|prog|brute|smart]\n");
	fprintf(stderr, "  -copy [none|all]              Metadata retention (default: none)\n"); // UPDATED
	fprintf(stderr, "  -b <splits>                   Number of spectral bit splits\n");
	fprintf(stderr, "  -d <interleave>               DC component interleaving (0 or 1)\n");
	fprintf(stderr, "  -allowarith                   Allow arithmetic encoding if it optimizes output footprint\n");
	fprintf(stderr, "  -noarith                      Force absolute Huffman decoding compliance across all files\n");
	fprintf(stderr, "  -q                            Quiet mode\n");
	fprintf(stderr, "  -s<N>                         Strip APP markers (N from 0 to 15)\n");
}

bool parse_command_line(int argc, char** argv, char** infile, char** outfile) {
	int arg_idx = 1;
	while (arg_idx < argc) {
		if (argv[arg_idx][0] == '-') {
			if (strcmp(argv[arg_idx], "-mode") == 0 && arg_idx + 1 < argc) {
				char* mode_str = argv[++arg_idx];
				if (strcmp(mode_str, "seq") == 0) {
					flag_run_mode = MODE_BASELINE_SEQ;
				} else if (strcmp(mode_str, "extseq") == 0) {
					flag_run_mode = MODE_EXTENDED_SEQ;
				} else if (strcmp(mode_str, "prog") == 0) {
					flag_run_mode = MODE_PROGRESSIVE;
				} else if (strcmp(mode_str, "brute") == 0) {
					flag_run_mode = MODE_BRUTE;
				} else if (strcmp(mode_str, "smart") == 0) {
					flag_run_mode = MODE_SMART;
				} else {
					return false;
				}
			} else if (strcmp(argv[arg_idx], "-copy") == 0 && arg_idx + 1 < argc) { // NEW
				char* copy_str = argv[++arg_idx];
				if (strcmp(copy_str, "all") == 0) {
					flag_copy_mode = COPY_ALL;
				} else {
					flag_copy_mode = COPY_NONE;
				}
			} else if (strcmp(argv[arg_idx], "-b") == 0 && arg_idx + 1 < argc) {
				flag_bit_splits = atoi(argv[++arg_idx]);
			} else if (strcmp(argv[arg_idx], "-d") == 0 && arg_idx + 1 < argc) {
				flag_dc_interleave = atoi(argv[++arg_idx]);
			} else if (strcmp(argv[arg_idx], "-allowarith") == 0) {
				flag_allow_arithmetic = true;
			} else if (strcmp(argv[arg_idx], "-noarith") == 0) {
				flag_force_no_arithmetic = true;
			} else if (strcmp(argv[arg_idx], "-q") == 0) {
				flag_quiet = true;
			} else if (strncmp(argv[arg_idx], "-s", 2) == 0 && strlen(argv[arg_idx]) > 2) {
				int app_val = atoi(argv[arg_idx] + 2);
				if (app_val >= 0 && app_val < 16)
					flag_strip_app[app_val] = true;
			}
		} else {
			if (!*infile)
				*infile = argv[arg_idx];
			else if (!*outfile)
				*outfile = argv[arg_idx];
		}
		arg_idx++;
	}
	return (*infile && *outfile);
}

size_t extract_target_scan_size(const unsigned char* buffer, size_t size, int target_idx) {
	if (size < 2 || buffer[0] != 0xFF || buffer[1] != 0xD8)
		return 0;
	size_t pos = 2;
	int current_scan_idx = -1;
	size_t scan_start_pos = 0;

	while (pos < size) {
		if (buffer[pos] == 0xFF) {
			unsigned char marker = buffer[pos + 1];
			while (marker == 0xFF) {
				pos++;
				marker = buffer[pos + 1];
			}
			if (marker == 0x00) {
				pos += 2;
				continue;
			}
			if (marker == 0xD9) {
				if (current_scan_idx == target_idx && scan_start_pos > 0) {
					return pos - scan_start_pos;
				}
				break;
			}
			if (marker == 0xDA) {
				if (current_scan_idx == target_idx && scan_start_pos > 0) {
					return pos - scan_start_pos;
				}
				current_scan_idx++;
				pos += 2;
				unsigned int len = (buffer[pos] << 8) | buffer[pos + 1];
				pos += len;
				scan_start_pos = pos;
				continue;
			}
			pos += 2;
			unsigned int len = (buffer[pos] << 8) | buffer[pos + 1];
			pos += len;
		} else {
			pos++;
		}
	}
	return 0;
}

/*
 * ============================================================================
 * PROGRESSIVE SCAN PRIMARY COMPARATOR
 * Natively emulates Perl's composite sort regex logicblock.
 * Sorts primarily by Se (Spectral End), using an explicit component string
 * comparison array fallback for matching boundaries to preserve stable order.
 * ============================================================================
 */
int compare_scans_parity(const void* a, const void* b) {
	const jpeg_scan_info* sa = (const jpeg_scan_info*) a;
	const jpeg_scan_info* sb = (const jpeg_scan_info*) b;

	// 1. Sort primarily by Se (Spectral End boundary) matching: $ab <=> $bb
	if (sa->Se != sb->Se) {
		return sa->Se - sb->Se;
	}

	// 2. Lexicographical string comparison fallback simulation: $ap cmp $bp
	char str_a[32] = { 0 };
	char str_b[32] = { 0 };

	if (sa->comps_in_scan > 1) {
		int pos = 0;
		for (int c = 0; c < sa->comps_in_scan; c++) {
			pos += sprintf(str_a + pos, "%d%s", sa->component_index[c], (c == sa->comps_in_scan - 1) ? "" : " ");
		}
	} else {
		sprintf(str_a, "%d", sa->component_index[0]);
	}

	if (sb->comps_in_scan > 1) {
		int pos = 0;
		for (int c = 0; c < sb->comps_in_scan; c++) {
			pos += sprintf(str_b + pos, "%d%s", sb->component_index[c], (c == sb->comps_in_scan - 1) ? "" : " ");
		}
	} else {
		sprintf(str_b, "%d", sb->component_index[0]);
	}

	int cmp_res = strcmp(str_a, str_b);
	if (cmp_res != 0) {
		return cmp_res;
	}

	// 3. STABLE TIE-BREAKERS: If Se and Component Strings are identical,
	// enforce deterministic tracking based on remaining parameters to prevent qsort drift.
	if (sa->Ss != sb->Ss) {
		return sa->Ss - sb->Ss;
	}
	if (sa->Ah != sb->Ah) {
		return sa->Ah - sb->Ah;
	}
	return sa->Al - sb->Al;
}

/*
 * HELPER DEPENDENCY FUNCTION: Emulates Perl's inside() subroutine range checker
 */
static bool inside_range(int val, int p, int q) { return (p <= val && val <= q); }

/*
 * HELPER COMPONENT COMPARE FUNCTION: Checks if plane string sets match or overlap
 */
static bool component_strings_match(const jpeg_scan_info* a, const jpeg_scan_info* b) {
	char str_a[32] = { 0 };
	char str_b[32] = { 0 };

	int pos = 0;
	for (int c = 0; c < a->comps_in_scan; c++) {
		pos += sprintf(str_a + pos, "%d ", a->component_index[c]);
	}
	pos = 0;
	for (int c = 0; c < b->comps_in_scan; c++) {
		pos += sprintf(str_b + pos, "%d ", b->component_index[c]);
	}
	return strcmp(str_a, str_b) == 0;
}

/*
 * ============================================================================
 * PROGRESSIVE LAYOUT DEPENDENCY GRAPH ENGINE
 * Accurate port of Perl's @prev tracking graph and 'loop:' traversal pass.
 * Maps exact multi-conditional dependencies over bit plane splits.
 * ============================================================================
 */
void sort_scans_topologically(jpeg_scan_info* scans, int num_scans) {
	if (num_scans <= 1)
		return;

	// 1. Dynamically build the exact dependency tracking matrix map (@prev)
	int* prev_count = (int*) calloc(num_scans, sizeof(int));
	int** prev_matrix = (int**) malloc(num_scans * sizeof(int*));
	for (int i = 0; i < num_scans; i++) {
		prev_matrix[i] = (int*) malloc(num_scans * sizeof(int));
	}

	for (int i = 0; i < num_scans; i++) {
		for (int j = 0; j < num_scans; j++) {
			if (i == j)
				continue;

			const jpeg_scan_info* si = &scans[i];
			const jpeg_scan_info* sj = &scans[j];

			bool is_dependent = false;

			// Condition A: Matches plane keys, overlapping boundaries, and sequential approximations
			if (component_strings_match(sj, si)
				&& (inside_range(si->Ss, sj->Ss, sj->Se) || inside_range(sj->Ss, si->Ss, si->Se)) && si->Al > sj->Al) {
				is_dependent = true;
			}
			// Condition B: Alphabetical/lexicographical progression layer constraint
			else {
				char str_i[32] = { 0 };
				char str_j[32] = { 0 };
				int pos = 0;
				for (int c = 0; c < si->comps_in_scan; c++)
					pos += sprintf(str_i + pos, "%d ", si->component_index[c]);
				pos = 0;
				for (int c = 0; c < sj->comps_in_scan; c++)
					pos += sprintf(str_j + pos, "%d ", sj->component_index[c]);

				if (strcmp(str_j, str_i) > 0 && sj->Se >= si->Se) {
					is_dependent = true;
				}
			}

			if (is_dependent) {
				prev_matrix[j][prev_count[j]++] = i;
			}
		}
	}

	// 2. Emulate Perl's 'loop:' state traversal to assemble order allocations (@bestout)
	jpeg_scan_info* sorted_output = (jpeg_scan_info*) malloc(num_scans * sizeof(jpeg_scan_info));
	bool* order_emitted = (bool*) calloc(num_scans, sizeof(bool));
	int emitted_count = 0;
	int i_iterator = -1;

	while (emitted_count < num_scans) {
		i_iterator++;
		if (i_iterator == num_scans) {
			i_iterator = 0;
		}

		if (order_emitted[i_iterator]) {
			continue;
		}

		bool dependencies_cleared = true;
		for (int d = 0; d < prev_count[i_iterator]; d++) {
			int required_idx = prev_matrix[i_iterator][d];
			if (!order_emitted[required_idx]) {
				dependencies_cleared = false;
				break;
			}
		}

		if (dependencies_cleared) {
			sorted_output[emitted_count++] = scans[i_iterator];
			order_emitted[i_iterator] = true;
			i_iterator = -1; // Reset iterator back to track root matches cleanly
		}
	}

	// 3. Commit the aligned structural matrix entries back to the primary buffer pointer
	memcpy(scans, sorted_output, num_scans * sizeof(jpeg_scan_info));

	// Cleanup dynamically allocated structures safely
	for (int i = 0; i < num_scans; i++)
		free(prev_matrix[i]);
	free(prev_matrix);
	free(prev_count);
	free(sorted_output);
	free(order_emitted);
}

int my_compare_scans_parity(const void* a, const void* b) {
	const jpeg_scan_info* sa = (const jpeg_scan_info*) a;
	const jpeg_scan_info* sb = (const jpeg_scan_info*) b;

	if (sa->Ss == 0 && sb->Ss > 0)
		return -1;
	if (sa->Ss > 0 && sb->Ss == 0)
		return 1;

	if (sa->Ss == 0 && sb->Ss == 0) {
		if (sa->comps_in_scan > 1 && sb->comps_in_scan == 1)
			return -1;
		if (sa->comps_in_scan == 1 && sb->comps_in_scan > 1)
			return 1;

		if (sa->comps_in_scan == 1 && sb->comps_in_scan == 1) {
			if (sa->component_index[0] != sb->component_index[0]) {
				return sa->component_index[0] - sb->component_index[0];
			}
		}

		if (sa->Ah != sb->Ah) {
			return sa->Ah - sb->Ah;
		}
		return sa->Al - sb->Al;
	}

	if (sa->Ss != sb->Ss) {
		return sa->Ss - sb->Ss;
	}

	if (sa->Se != sb->Se) {
		return sa->Se - sb->Se;
	}

	if (sa->component_index[0] != sb->component_index[0]) {
		return sa->component_index[0] - sb->component_index[0];
	}

	if (sa->Ah != sb->Ah) {
		return sa->Ah - sb->Ah;
	}

	return sa->Al - sb->Al;
}

static bool scan_depends_on(const jpeg_scan_info* a, const jpeg_scan_info* b) {
	if (a->Ss != b->Ss) {
		return a->Ss < b->Ss;
	}
	if (a->Ah != b->Ah) {
		return a->Ah < b->Ah;
	}
	if (a->Al != b->Al) {
		return a->Al < b->Al;
	}
	if (a->component_index[0] != b->component_index[0]) {
		return a->component_index[0] < b->component_index[0];
	}
	return false;
}

void my_sort_scans_topologically(jpeg_scan_info* scans, int num_scans) {
	if (num_scans <= 1)
		return;

	jpeg_scan_info* sorted = malloc(num_scans * sizeof(jpeg_scan_info));
	bool* emitted = calloc(num_scans, sizeof(bool));
	int sorted_count = 0;

	for (int i = 0; i < num_scans; i++) {
		if (scans[i].Ss == 0) {
			sorted[sorted_count++] = scans[i];
			emitted[i] = true;
		}
	}

	while (sorted_count < num_scans) {
		bool advanced = false;
		for (int i = 0; i < num_scans; i++) {
			if (emitted[i])
				continue;

			bool ready = true;
			for (int j = 0; j < num_scans; j++) {
				if (emitted[j] || i == j)
					continue;
				if (scan_depends_on(&scans[j], &scans[i])) {
					ready = false;
					break;
				}
			}

			if (ready) {
				sorted[sorted_count++] = scans[i];
				emitted[i] = true;
				advanced = true;
			}
		}

		if (!advanced) {
			for (int i = 0; i < num_scans; i++) {
				if (!emitted[i]) {
					sorted[sorted_count++] = scans[i];
					emitted[i] = true;
					break;
				}
			}
		}
	}

	memcpy(scans, sorted, num_scans * sizeof(jpeg_scan_info));
	free(sorted);
	free(emitted);
}

/*
 * ============================================================================
 * STAGE 3 & 4 LOW-LEVEL BINARY STRUCTURE AUDITING SUITE
 * Decodes the compiled memory buffers to parse and trace structural markers,
 * scan sizes, application payloads, and component dimensions.
 * ============================================================================
 */
void audit_binary_structure(const unsigned char* buf, size_t size) {
	if (size < 2 || buf[0] != 0xFF || buf[1] != 0xD8) {
		printf("[AUDIT_PANIC] Invalid or unaligned JPEG SOI container.\n");
		return;
	}

	printf("[TRACE_BINARY_STRUCTURE_START]\n");
	printf("CONTAINER_PROPERTIES: TotalBytes=%zu\n", size);

	size_t pos = 2;
	int scan_counter = 0;
	size_t current_scan_payload = 0;
	bool inside_scan_payload = false;

	while (pos < size) {
		if (buf[pos] == 0xFF) {
			// Handle standard multi-byte padding sequences safely
			unsigned char marker = buf[pos + 1];
			while (marker == 0xFF && pos < size - 1) {
				pos++;
				marker = buf[pos + 1];
			}
			if (marker == 0x00) {
				if (inside_scan_payload) {
					current_scan_payload += 2;
				}
				pos += 2;
				continue;
			}

			// Flush out active entropy-coded payload statistics on next structural boundary
			if (inside_scan_payload) {
				printf("SCAN_ENTROPY_BODY [%02d]: PayloadBytes=%zu\n", scan_counter, current_scan_payload);
				current_scan_payload = 0;
				inside_scan_payload = false;
				scan_counter++;
			}

			unsigned int marker_length = 0;
			// Exclude standalone structural markers without an explicit payload size segment
			if (marker != 0xD8 && marker != 0xD9 && (marker < 0xD0 || marker > 0xD7)) {
				if (pos + 3 < size) {
					marker_length = (buf[pos + 2] << 8) | buf[pos + 3];
				}
			}

			// Group marker tokens into logical human-scannable blocks
			if (marker >= 0xC0 && marker <= 0xCF && marker != 0xC4 && marker != 0xC8 && marker != 0xCC) {
				printf("MARKER_NODE: Type=SOF%d(0x%02X) | SegmentBytes=%u\n", marker - 0xC0, marker, marker_length);
			} else if (marker == 0xC4) {
				printf("MARKER_NODE: Type=DHT(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
			} else if (marker == 0xDB) {
				printf("MARKER_NODE: Type=DQT(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
			} else if (marker == 0xDD) {
				printf("MARKER_NODE: Type=DRI(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
			} else if (marker == 0xDA) {
				printf("MARKER_NODE: Type=SOS(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
				inside_scan_payload = true;
				// Pos + 2 (Marker prefix) + length fields sets index to raw entropy boundaries
				pos += (2 + marker_length);
				continue;
			} else if (marker >= 0xE0 && marker <= 0xEF) {
				printf("MARKER_NODE: Type=APP%d(0x%02X) | SegmentBytes=%u\n", marker - 0xE0, marker, marker_length);
			} else if (marker == 0xFE) {
				printf("MARKER_NODE: Type=COM(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
			} else if (marker == 0xD9) {
				printf("MARKER_NODE: Type=EOI(0x%02X) | SegmentBytes=0\n", marker);
			} else {
				printf("MARKER_NODE: Type=UNKNOWN(0x%02X) | SegmentBytes=%u\n", marker, marker_length);
			}

			pos += (marker_length > 0 ? marker_length + 2 : 2);
		} else {
			if (inside_scan_payload) {
				current_scan_payload++;
			}
			pos++;
		}
	}

	printf("[TRACE_BINARY_STRUCTURE_END]\n");
	fflush(stdout);
}

/*
 * ============================================================================
 * REFACTORED METADATA CONFIGURATION CONTROLLER
 * Iterates through saved source image markers and safely writes them into
 * the compression pipeline, neutralizing state machine collisions.
 * ============================================================================
 */
void configure_metadata_copy_pipeline(j_compress_ptr cinfo, j_decompress_ptr dinfo) {
	if (flag_copy_mode == COPY_ALL) {
		// Let the library track context defaults natively
		cinfo->write_Adobe_marker = FALSE;
		cinfo->write_JFIF_header = TRUE;

		jpeg_saved_marker_ptr curr_marker = dinfo->marker_list;
		while (curr_marker != NULL) {
			int app_id = curr_marker->marker - JPEG_APP0;
			bool clear_to_write = true;

			// FIX: Only skip APP0 (JFIF) since libjpeg-turbo auto-synthesizes it.
			// Allow APP14 (Adobe) and all other custom segments to be written explicitly.
			if (curr_marker->marker == (JPEG_APP0 + 0)) {
				clear_to_write = false;
			}

			if (app_id >= 0 && app_id < 16) {
				if (flag_strip_app[app_id]) {
					clear_to_write = false;
				}
			}

			if (clear_to_write) {
				jpeg_write_marker(cinfo, curr_marker->marker, curr_marker->data, curr_marker->data_length);
			}
			curr_marker = curr_marker->next;
		}
	} else {
		// Strict optimized stripped default configuration parameters
		cinfo->write_Adobe_marker = FALSE;
		cinfo->write_JFIF_header = FALSE;

		for (int app_idx = 0; app_idx < 16; app_idx++) {
			if (flag_strip_app[app_idx]) {
				jpeg_write_marker(cinfo, JPEG_APP0 + app_idx, NULL, 0);
			}
		}
	}
}
