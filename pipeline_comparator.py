#!/usr/bin/env python3
import re
import sys
import os
import subprocess
import argparse

def parse_trace_output(output_text, is_c_port=False):
    matrix_costs = {}
    final_script = []
    in_final_script_block = False

    for line in output_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Parse final layout script blocks if present
        if "[TRACE_FINAL_SCRIPT_START]" in line:
            in_final_script_block = True
            continue
        if "[TRACE_FINAL_SCRIPT_END]" in line:
            in_final_script_block = False
            continue

        if in_final_script_block:
            if is_c_port:
                if "SCRIPT_SCAN:" in line:
                    m = re.search(r"Script=\{(.*?)\}", line)
                    if m:
                        final_script.append(m.group(1).replace(";", "").strip())
            else:
                script_m = re.search(
                    r"SCAN\s+\d+:\s*Comps=\d+,\s*Component_Idx_0=(.*?),\s*Ss=(\d+),\s*Se=(\d+),\s*Ah=(\d+),\s*Al=(\d+)",
                    line
                )
                if script_m:
                    comps, ss, se, ah, al = script_m.groups()
                    canonical_scan = f"{comps.strip()}: {ss.strip()} {se.strip()} {ah.strip()} {al.strip()}"
                    final_script.append(canonical_scan)
            continue

        if is_c_port:
            # STRICT C PORT PARSER: Only accept lines matching our exact format and ignore fallbacks
            if ":" in line and ";" in line:
                if "bytes" in line or "Change:" in line or "SCRIPT_SCAN" in line or "LANDMARK" in line or "STOP" in line or "TRACE_STAGE2" in line or "RAW_TREE" in line or "STAGE2_DC" in line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        cost_val = int(parts[-1])
                        key_part = " ".join(parts[:-1])
                        # Remove semicolon completely to ensure strict token keys
                        key_clean = key_part.replace(";", "").strip()
                        key_clean = re.sub(r"\s+", " ", key_clean)

                        # Filter out global AC sweep dummy baseline helper elements (Al = 9)
                        params_check = key_clean.split(":")[-1].strip().split()
                        if len(params_check) == 4 and int(params_check[-1]) == 9:
                            continue

                        matrix_costs[key_clean] = cost_val
                    except ValueError:
                        continue
        else:
            # PERL REFERENCE PARSER
            if ":" in line and (" " in line or ";" in line):
                if "bytes" in line or "Change:" in line or "Size" in line:
                    continue

                if "MATRIX_CELL" in line:
                    m = re.search(r"P:(\d+)\s*\|\s*Ss:(\d+)\s*\|\s*Se:(\d+)\s*\|\s*Span:\d+\s*\|\s*Al:(\d+)\s*\|\s*Cost:(\d+)", line)
                    if m:
                        p, ss, se, al, cost_val = m.groups()
                        # Reconstruct the canonical token string key
                        key_clean = f"{p}: {int(ss)} {int(se)} 0 {int(al)}"
                        matrix_costs[key_clean] = int(cost_val)
                    continue

                parts = line.split()
                if len(parts) >= 2:
                    try:
                        cost_val = int(parts[-1])
                        key_part = " ".join(parts[:-1])
                        key_clean = key_part.replace(";", "").strip()
                        key_clean = re.sub(r"\s+", " ", key_clean)

                        params_check = key_clean.split(":")[-1].strip().split()
                        if len(params_check) == 4 and int(params_check[-1]) == 9:
                            continue

                        matrix_costs[key_clean] = cost_val
                    except ValueError:
                        continue

    return matrix_costs, final_script

def compute_dead_key_statistics(perl_only_set):
    # Strip any remaining loose summary string text junk tokens
    filtered_dead_keys = [k for k in perl_only_set if k.strip() and "Size" not in k and "Change" not in k]

    if not filtered_dead_keys:
        print("\n  - [DIAGNOSTIC SWEEP] STATISTICAL ANALYSIS: 0 Functional Operational Matrix Keys Missing! (True Parity)")
        return

    print(f"\n  - [DIAGNOSTIC SWEEP] STATISTICAL ANALYSIS OF {len(filtered_dead_keys)} FUNCTIONAL DEAD KEYS:")
    print("    " + "-" * 70)

    comp_groups = {}
    spectral_ranges = {"DC (0-0)": 0, "AC (1-63)": 0}
    al_bit_distributions = {}
    ah_bit_distributions = {}

    for key in filtered_dead_keys:
        if ":" in key:
            comps_part, params_part = key.split(":")
            comps_key = comps_part.strip()
            comp_groups[comps_key] = comp_groups.get(comps_key, 0) + 1

            params = params_part.strip().split()
            if len(params) == 4:
                ss, se, ah, al = map(int, params)
                if ss == 0 and se == 0:
                    spectral_ranges["DC (0-0)"] += 1
                else:
                    spectral_ranges["AC (1-63)"] += 1

                al_bit_distributions[al] = al_bit_distributions.get(al, 0) + 1
                ah_bit_distributions[ah] = ah_bit_distributions.get(ah, 0) + 1

    print("    1. COMPONENT PLANE SEPARATION DISTRIBUTIONS:")
    for comp, count in sorted(comp_groups.items()):
        print(f"       -> Plane Profile '{comp}': {count} keys missing")

    print("\n    2. SPECTRAL COEFFICIENT BOUNDARY GROUPS:")
    for spec, count in spectral_ranges.items():
        print(f"       -> Range Category '{spec}': {count} keys missing")

    print("\n    3. SUCCESSIVE APPROXIMATION AL-BIT DEPTH FREQUENCIES:")
    for al, count in sorted(al_bit_distributions.items()):
        print(f"       -> Al Bit Position {al}: {count} keys missing")

    print("\n    4. PROGRESSIVE ANCHOR AH-BIT REFINE FREQUENCIES:")
    for ah in sorted(ah_bit_distributions.keys()):
        print(f"       -> Ah Bit Position {ah}: {ah_bit_distributions[ah]} keys missing")
    print("    " + "-" * 70)

def analyze_matrix_divergence(perl_mat, c_mat):
    common_keys = set(perl_mat.keys()).intersection(set(c_mat.keys()))
    perl_only = set(perl_mat.keys()) - set(c_mat.keys())
    c_only = set(c_mat.keys()) - set(perl_mat.keys())

    mismatches = []
    total_variance = 0
    dc_errors, ac_errors = 0, 0

    for key in common_keys:
        p_cost = perl_mat[key]
        c_cost = c_mat[key]
        if p_cost != c_cost:
            variance = c_cost - p_cost
            mismatches.append((key, p_cost, c_cost, variance))
            total_variance += abs(variance)
            if ": 0 0 " in key or (key.startswith("0 ") and " 0 0 " in key):
                dc_errors += 1
            else:
                ac_errors += 1

    # Sort mismatches by absolute delta magnitude to find worst formula errors
    sorted_mismatches = sorted(mismatches, key=lambda x: abs(x[3]), reverse=True)

    stats = {
        "common_count": len(common_keys),
        "perl_only_count": len(perl_only),
        "c_only_count": len(c_only),
        "mismatch_count": len(mismatches),
        "mean_absolute_variance": (total_variance / len(mismatches)) if mismatches else 0.0,
        "dc_mismatch_count": dc_errors,
        "ac_mismatch_count": ac_errors,
        "top_20_mismatches": sorted_mismatches[:20],
        "perl_only_sample": sorted(list(perl_only))[:20],
        "c_only_sample": sorted(list(c_only))[:20]
    }
    return stats

def parse_audit_blocks(output_text):
    """
    Parses and builds sequential structural tracking matrices for marker blocks
    and entropy segments, normalizing out unaligned application metadata blocks.
    """
    markers = []
    entropy_scans = []
    in_audit_block = False

    for line in output_text.splitlines():
        line = line.strip()
        if "[TRACE_BINARY_STRUCTURE_START]" in line:
            in_audit_block = True
            continue
        if "[TRACE_BINARY_STRUCTURE_END]" in line:
            in_audit_block = False
            continue

        if in_audit_block:
            if line.startswith("MARKER_NODE:"):
                m_type_match = re.search(r"Type=(.*?)(?:\s*\||$)", line)
                m_size_match = re.search(r"SegmentBytes=(\d+)", line)
                if m_type_match and m_size_match:
                    m_type = m_type_match.group(1).strip()
                    m_size = int(m_size_match.group(1))

                    # Normalizing out unaligned non-codec APP frames (APP0 - APP15)
                    if m_type.startswith("APP"):
                        continue

                    markers.append({
                        "type": m_type,
                        "size": m_size
                    })
            elif line.startswith("SCAN_ENTROPY_BODY"):
                m_idx = re.search(r"\[(\d+)\]", line)
                m_pbytes = re.search(r"PayloadBytes=(\d+)", line)
                if m_idx and m_pbytes:
                    entropy_scans.append({
                        "idx": int(m_idx.group(1)),
                        "bytes": int(m_pbytes.group(1))
                    })
    return markers, entropy_scans

def run_perl_reference_audit(perl_script_path, input_image, output_target):
    """
    Executes the Perl baseline script with standard options and passes the output
    directly to a dynamic baseline parser.
    """
    cmd = ["perl", perl_script_path, "-v", input_image, output_target]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.stdout

def analyze_structural_alignment(p_markers, p_entropy, c_markers, c_entropy):
    print("\n" + "="*78)
    print("   STAGE 3 & 4 DIAGNOSTIC: BINARY CONTAINER ALIGNMENT REPORT")
    print("="*78)

    # 1. Structural Marker Alignment Audit
    print(" STAGE 3: STRUCTURE MARKER ELEMENT MAP:")
    print("    " + "-"*70)
    max_m = max(len(p_markers), len(c_markers))
    marker_diverged = False

    for i in range(max_m):
        p_m = p_markers[i] if i < len(p_markers) else {"type": "MISSING", "size": 0}
        c_m = c_markers[i] if i < len(c_markers) else {"type": "MISSING", "size": 0}

        p_str = f"{p_m['type']}({p_m['size']}B)" if p_m["type"] != "MISSING" else "MISSING"
        c_str = f"{c_m['type']}({c_m['size']}B)" if c_m["type"] != "MISSING" else "MISSING"

        status = "✅ OK"
        if p_m["type"] !=  c_m["type"] or p_m["size"] != c_m["size"]:
            status = "❌ DISCREPANCY"
            marker_diverged = True

        if i < 25 or p_m["type"] != c_m["type"]:
            print(f"      Node [{i:02d}]: Reference-Perl={p_str:<22} | Ported-C={c_str:<22} | {status}")

    # 2. Sequential Entropy Coding Body Analysis
    print("\n STAGE 4: ENTROPY PAYLOAD ALLOCATION MAP:")
    print("    " + "-"*70)
    max_e = max(len(p_entropy), len(c_entropy))
    entropy_diverged = False

    for i in range(max_e):
        p_e = p_entropy[i] if i < len(p_entropy) else {"bytes": 0}
        c_e = c_entropy[i] if i < len(c_entropy) else {"bytes": 0}

        delta = c_e["bytes"] - p_e["bytes"]
        status = "✅ MATCH" if delta == 0 else f"⚠️ DELTA: {delta:+} Bytes"
        if delta != 0:
            entropy_diverged = True

        print(f"      Scan [{i:02d}]: Perl-Bytes={p_e['bytes']:<8} | C-Bytes={c_e['bytes']:<8} | {status}")

    print("\n" + "="*78)
    m_status = "PARITY SECURED ✅" if not marker_diverged else "STRUCTURAL DELTAS DETECTED ❌"
    e_status = "PARITY SECURED ✅" if not entropy_diverged else "BITSTREAM ALLOCATION DELTAS DETECTED ❌"
    print(f" FINAL PARITY STATUS -> STAGE 3 (MARKERS): {m_status}")
    print(f"                        STAGE 4 (BITSTREAM): {e_status}")
    print("="*78)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", help="Input image path")
    parser.add_argument("--binary", default="./jpeg-ultra-scan-c", help="Binary location override")
    args = parser.parse_args()

    input_image = args.image
    c_binary_path = args.binary

    base = os.path.basename(input_image)
    perl_log = f"./.cache_comparator_perl/{base}.perl_trace.log"
    os.makedirs("./.cache_comparator_c", exist_ok=True)
    tmp_c_out = f"./.cache_comparator_c/{base}.c_out.jpg"

    if not os.path.exists(perl_log):
        print(f"[!] Error: Perl trace log missing at {perl_log}. Run Perl pass first.")
        sys.exit(1)


    if not os.path.exists(perl_log):
        print(f"[!] Error: Perl trace log missing at {perl_log}. Run Perl pass first.")
        sys.exit(1)

    with open(perl_log, "r") as f:
        perl_raw = f.read()

    print(f"[*] Processing statistical cross-audit for: {base}")
    c_res = subprocess.run(
        [c_binary_path, "-mode", "prog", "-copy", "all", input_image, tmp_c_out],
        capture_output=True,
        text=True
    )

    # TELEMETRY GUARD: Print internal panics or runtime error traps explicitly
    if c_res.returncode != 0:
        print(f"[!] C Engine execution failed with exit code {c_res.returncode}")

        pre_sort_lines = []
        in_pre_sort = False
        for line in c_res.stdout.splitlines():
            if "[TRACE_STAGE2_PRE_SORT_START]" in line:
                in_pre_sort = True
                continue
            if "[TRACE_STAGE2_PRE_SORT_END]" in line:
                in_pre_sort = False
                continue
            if in_pre_sort:
                pre_sort_lines.append(line)

        if pre_sort_lines:
            print("\n  - [COMPILER TRACE] STAGE 2 PRE-SORT METRIC CAPTURE:")
            print("    " + "-" * 70)
            for line in pre_sort_lines[:40]:
                print(f"       -> {line}")
            print("    " + "-" * 70)

        if c_res.stderr:
            print(f"[!] Stderr Trace:\n{c_res.stderr}")
    else:
        # Success path tracking: Parse out any final or intermediate script traces
        pass


    p_mat, p_script = parse_trace_output(perl_raw, is_c_port=False)
    c_mat, c_script = parse_trace_output(c_res.stdout, is_c_port=True)

    stats = analyze_matrix_divergence(p_mat, c_mat)

    print("\n" + "="*78)
    print("   JPEG-ULTRA-SCAN-C EXHAUSTIVE PIPELINE DIVERGENCE REPORT")
    print("="*78)
    print(" STAGE 1: COST METRIC CACHE MATRIX ANALYSIS")
    print(f"  - Total Matrix Cells -> Reference Perl: {len(p_mat):<6} | Ported C Engine: {len(c_mat):<6}")
    print(f"  - Overlapping Cells  : {stats['common_count']}")
    print(f"  - Discrepancy Cells  : {stats['mismatch_count']} (DC Mismatches: {stats['dc_mismatch_count']}, AC Mismatches: {stats['ac_mismatch_count']})")

    if stats['mismatch_count'] > 0:
        print(f"  - Mean Byte Variance: {stats['mean_absolute_variance']:.2f} Bytes / Cell")
        print("\n  - TOP 20 CRITICAL MATRIX CELL DISCREPANCIES (Key | Perl -> C | Delta):")
        print("    " + "-"*70)
        for key, p_c, c_c, diff in stats['top_20_mismatches']:
            print(f"      -> {key:<18} | {p_c:<5} -> {c_c:<5} | {diff:+}B")

    if stats['perl_only_count'] > 0:
        print(f"\n  - DEAD KEYS IN C (Active in Perl but entirely uncomputed in C, Count: {stats['perl_only_count']}):")
        print("    " + "-"*70)
        for k in stats['perl_only_sample']:
            print(f"      -> Missing Key: {k}")

        compute_dead_key_statistics(set(p_mat.keys()) - set(c_mat.keys()))

    if stats['c_only_count'] > 0:
        print(f"\n  - ORPHAN KEYS IN C (Computed in C but completely missing from Perl, Count: {stats['c_only_count']}):")
        print("    " + "-"*70)
        for k in stats['c_only_sample']:
            print(f"      -> Extra Key  : {k}")

    print("\n" + "-"*78)
    print(" STAGE 2: PROGRESSIVE LAYOUT SCRIPT ANALYSIS")
    print(f"  - Total Scans Ordered -> Reference Perl: {len(p_script):<6} | Ported C Engine: {len(c_script):<6}")

    script_diverged = False
    max_scans = max(len(p_script), len(c_script))
    if max_scans > 0:
        print("\n  - PROGRESSIVE STRATEGY SCAN ALIGNMENT DATA:")
        print("    " + "-"*70)
        for i in range(max_scans):
            p_scan = p_script[i] if i < len(p_script) else "MISSING"
            c_scan = c_script[i] if i < len(c_script) else "MISSING"
            marker = "❌ DIVERGED" if p_scan != c_scan else "✅ OK"
            if i < 20 or p_scan != c_scan: # Print top 20 or first error point
                print(f"      -> Scan [{i:02d}]: Perl={p_scan:<14} | C={c_scan:<14} | {marker}")
            if p_scan != c_scan and not script_diverged:
                script_diverged = True

    # ... code context: printing STAGE 1 and STAGE 2 details ...
    print("\n" + "-"*78)
    s1_status = "MATCH ✅" if (stats['mismatch_count'] == 0 and len(p_mat) > 0 and len(c_mat) > 0) else "DIVERGED ❌"
    s2_status = "MATCH ✅" if (not script_diverged and len(p_script) == len(c_script) and len(p_script) > 0) else "DIVERGED ❌"
    print(f" FINAL PARITY STATUS -> STAGE 1: {s1_status} | STAGE 2: {s2_status}")
    print("="*78 + "\n")

    # STAGE 3 & 4 DIAGNOSTIC LOG BLOCKS EMBEDDED SAFELY AT THE BOTTOM
    perl_markers, perl_entropy = parse_audit_blocks(perl_raw)
    c_markers, c_entropy = parse_audit_blocks(c_res.stdout)

    if perl_markers or c_markers:
        analyze_structural_alignment(perl_markers, perl_entropy, c_markers, c_entropy)

if __name__ == "__main__":
    main()
