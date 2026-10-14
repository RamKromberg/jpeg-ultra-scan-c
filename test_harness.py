#!/usr/bin/env python3
import os
import sys
import glob
import time
import math
import argparse
import subprocess

TEST_DIR = "./test_images"
CACHE_DIR = "./.cache_perl_baselines"
C_OUT_DIR = "./.cache_c_outputs"
MASTER_REPORT = "log0.log"
C_PORT = "./jpeg-ultra-scan-c"
PERL_SCRIPT = "jpegultrascan" # the original script wrapped via nix derivation in shell.nix

SIMD_ENABLED = True
BENCHMARK_MODE = False

def run_command(cmd, timeout=10800):
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT EXPIRED"
    except Exception as e:
        return -2, "", f"EXECUTION FAILED: {str(e)}"

def get_detailed_meta(filepath):
    props = {"dimensions": "Unknown", "process": "Unknown", "bits": "8", "components": "3"}
    if not os.path.exists(filepath):
        return props
    
    rc, out, _ = run_command(["exiftool", "-ImageWidth", "-ImageHeight", "-EncodingProcess", "-BitsPerSample", "-ColorComponents", filepath])
    if rc == 0:
        mapping = {}
        for line in out.strip().split('\n'):
            if ":" in line:
                k, v = line.split(":", 1)
                mapping[k.strip().replace(" ", "")] = v.strip()
        
        w = mapping.get("ImageWidth", "")
        h = mapping.get("ImageHeight", "")
        if w and h:
            props["dimensions"] = f"{w}x{h}"
            
        proc = mapping.get("EncodingProcess", "")
        if "baseline" in proc.lower() or "sof0" in proc.lower():
            props["process"] = "Baseline"
        elif "extended" in proc.lower() or "sof1" in proc.lower():
            props["process"] = "Ext-Seq"
        elif "progressive" in proc.lower() and "arithmetic" not in proc.lower():
            props["process"] = "Prog-Huff"
        elif "arithmetic" in proc.lower() and "progressive" not in proc.lower():
            props["process"] = "Seq-Arith"
        elif "progressive arithmetic" in proc.lower():
            props["process"] = "Prog-Arith"
        else:
            props["process"] = proc if proc else "Unknown"
            
        props["bits"] = mapping.get("BitsPerSample", "8")
        
    return props

def get_djpeg_perf(filepath, iterations=10):
    if not os.path.exists(filepath):
        return "-", "N/A"
    
    if not BENCHMARK_MODE:
        rc, _, stderr = run_command(["djpeg", "-verbose", "-outfile", "/dev/null", filepath])
        if rc != 0:
            return "-", "ERR"
        scan_count = sum(1 for line in stderr.splitlines() if "Start Of Scan" in line)
        scan_str = f"{scan_count}scns" if scan_count > 0 else "1scn"
        return "-", scan_str
        
    times_ms = []
    scan_count = 0
    
    for i in range(iterations):
        t_start = time.time()
        rc, _, stderr = run_command(["djpeg", "-verbose", "-outfile", "/dev/null", filepath])
        t_diff = (time.time() - t_start) * 1000.0
        
        if rc != 0:
            return "ERR", "ERR"
            
        times_ms.append(t_diff)
        if i == 0:
            scan_count = sum(1 for line in stderr.splitlines() if "Start Of Scan" in line)

    mean_val = sum(times_ms) / iterations
    variance = sum((x - mean_val) ** 2 for x in times_ms) / iterations
    std_dev = math.sqrt(variance)
    
    scan_str = f"{scan_count}scns" if scan_count > 0 else "1scn"
    metrics_str = f"{mean_val:.2f}±{std_dev:.2f}ms"
    
    return metrics_str, scan_str

def get_tjbench_perf(filepath):
    if not os.path.exists(filepath):
        return "-", "-"
        
    if not BENCHMARK_MODE:
        return "-", "-"
    
    cmd = ["tjbench", filepath, "-strict", "-lossless", "-warmup", "0.5", "-benchtime", "1.0"]
    if not SIMD_ENABLED:
        cmd.extend(["-dct", "fast", "-nosmooth"])
        
    rc, stdout, stderr = run_command(cmd)
    if rc != 0 or not stdout:
        return "ERR", "ERR"
    
    fps = "ERR"
    mpsec = "ERR"
    
    for line in stdout.splitlines():
        if "Frame rate:" in line:
            try:
                fps = f"{float(line.split()[-2]):.1f}fps"
            except (ValueError, IndexError):
                pass
        elif "Throughput:" in line:
            try:
                mpsec = f"{float(line.split()[-2]):.1f}M/s"
            except (ValueError, IndexError):
                pass
                
    return fps, mpsec

def main():
    global SIMD_ENABLED, BENCHMARK_MODE
    
    parser = argparse.ArgumentParser(description="JPEG-ULTRA-SCAN-C Advanced Compacted Profiling Harness")
    parser.add_argument("--nosimd", action="store_true", help="Disable internal SIMD optimization pathways")
    parser.add_argument("--bench", action="store_true", help="Enable hardware benchmarking tracking grids")
    parser.add_argument("--binary", default="./jpeg-ultra-scan-c", help="Path to target executable binary")
    args = parser.parse_args()
    
    global C_PORT
    C_PORT = args.binary
    
    if args.nosimd:
        SIMD_ENABLED = False
    if args.bench:
        BENCHMARK_MODE = True

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(C_OUT_DIR, exist_ok=True)
    
    with open(MASTER_REPORT, "w") as r:
        r.write(f"=== JPEG-ULTRA-SCAN-C CROSS AUDIT LOG ===\nTimestamp: {time.asctime()}\n")

    images = sorted(glob.glob(os.path.join(TEST_DIR, "*.jpg")) + glob.glob(os.path.join(TEST_DIR, "*.jpeg")))
    
    # Path Sanity Check: Prevent silent layout skips if the target directory is empty
    if not images:
        print(f"\n>>> HARNESS HALT: No valid target assets (*.jpg, *.jpeg) found inside '{TEST_DIR}'! <<<")
        print("Please check your file system paths or match token extensions.\n")
        return

    # Integrated compact status tracking directly into the harness description line
    simd_suffix = "in SIMD" if SIMD_ENABLED else "no SIMD"
    bench_suffix = ", intensive benchmarking" if BENCHMARK_MODE else ""
    print(f"Running pythonized multi-image benchmarking harness ({simd_suffix}{bench_suffix})...")

    # Structure columns and formatting rules cleanly based on benchmark flags
    if BENCHMARK_MODE:
        header = f"{'Pipeline Target':<15} | {'Profile Properties':<22} | {'Size':<8} | {'Runtime':<8} | {'Decomp (Avg±SD)':<18} | {'tj Frame Rate':<13} | {'tj Throughput':<13} | {'Delta / Status':<14}"
        line_len = 164
    else:
        header = f"{'Pipeline Target':<15} | {'Profile Properties':<22} | {'Size':<8} | {'Runtime':<8} | {'Delta / Status':<14}"
        line_len = 84

    print(f"\n{header}")
    print("=" * line_len)
    
    for img in images:
        base = os.path.basename(img)
        meta_orig = get_detailed_meta(img)
        info_orig = f"{meta_orig['dimensions']} {meta_orig['process']} ({meta_orig['bits']}b)"
        orig_size = os.path.getsize(img)
        
        print(f"[{base}]")
        
        cached_perl = os.path.join(CACHE_DIR, f"{base}.perl.jpg")
        cached_log = os.path.join(CACHE_DIR, f"{base}.perl.log")
        
        sizes = {"orig": orig_size, "perl": "N/A"}
        times = {"perl": "-"}
        
        if not os.path.exists(cached_perl) or not os.path.exists(cached_log):
            t_start = time.time()
            rc_p, _, _ = run_command([PERL_SCRIPT, "-q", img, cached_perl])
            t_diff = time.time() - t_start
            if rc_p == 0:
                with open(cached_log, "w") as lf: lf.write(f"{t_diff:.3f}")
                times["perl"] = f"{t_diff:.3f}s"
            else:
                times["perl"] = "ERR"
        else:
            with open(cached_log, "r") as lf:
                times["perl"] = f"{lf.read().strip()}s"
                
        if os.path.exists(cached_perl):
            sizes["perl"] = os.path.getsize(cached_perl)
            meta_perl = get_detailed_meta(cached_perl)
            info_perl = f"{meta_perl['dimensions']} {meta_perl['process']} ({meta_perl['bits']}b)"
            perl_decomp_t, perl_scans = get_djpeg_perf(cached_perl)
            decomp_perl_str = f"{perl_decomp_t} ({perl_scans})" if perl_decomp_t != "-" else f"({perl_scans})"
            perl_tj_fps, perl_tj_mp = get_tjbench_perf(cached_perl)
        else:
            info_perl = "Missing"
            decomp_perl_str = "N/A"
            perl_tj_fps, perl_tj_mp = "-", "-"

        if isinstance(sizes["perl"], int):
            perl_diff = sizes["perl"] - orig_size
            perl_delta_str = f"{perl_diff} (WIN)" if perl_diff < 0 else (f"+{perl_diff} (LOSE)" if perl_diff > 0 else "0 (PARITY)")
        else:
            perl_delta_str = "N/A"

        orig_decomp_t, orig_scans = get_djpeg_perf(img)
        decomp_orig_str = f"{orig_decomp_t} ({orig_scans})" if orig_decomp_t != "-" else f"({orig_scans})"
        orig_tj_fps, orig_tj_mp = get_tjbench_perf(img)

        if BENCHMARK_MODE:
            print(f"  {'Original':<13} | {info_orig:<22} | {sizes['orig']:<8} | {'-':<8} | {decomp_orig_str:<18} | {orig_tj_fps:<13} | {orig_tj_mp:<13} | {'REF':<14}")
            print(f"  {'Perl':<13} | {info_perl:<22} | {sizes['perl']:<8} | {times['perl']:<8} | {decomp_perl_str:<18} | {perl_tj_fps:<13} | {perl_tj_mp:<13} | {perl_delta_str:<14}")
        else:
            print(f"  {'Original':<13} | {info_orig:<22} | {sizes['orig']:<8} | {'-':<8} | {'REF':<14}")
            print(f"  {'Perl':<13} | {info_perl:<22} | {sizes['perl']:<8} | {times['perl']:<8} | {perl_delta_str:<14}")

        target_modes = [
            ("seq", [], "C Baseline"), 
            ("extseq", [], "C Ext-Seq"), 
            ("prog", [], "C Prog-Stripped"),
            ("prog", ["-copy", "all"], "C Prog-Parity")
        ]
        for mode_flag, extra_flags, label in target_modes:
            # If tracking parity compliance mode, adjust the cache target filename to prevent overwrites
            file_suffix = f"{mode_flag}.parity" if "-copy" in extra_flags else mode_flag
            out_c = os.path.join(C_OUT_DIR, f"{base}.{file_suffix}.jpg")
            
            if os.path.exists(out_c):
                os.remove(out_c)
            
            t_start_c = time.time()
            
            # Construct execution parameters dynamically incorporating the metadata flags
            cmd_c = [C_PORT, "-mode", mode_flag] + extra_flags + ["-q", img, out_c]
            rc_c, stdout_c, stderr_c = run_command(cmd_c)
            
            time_c_str = f"{(time.time() - t_start_c):.3f}s"
                
            if rc_c != 0 or not os.path.exists(out_c):
                c_delta_report = "[CRASH] ❌"
                info_c = "CRASH"
                size_c = "FAILED"
                decomp_c_str = "N/A"
                c_tj_fps, c_tj_mp = "N/A", "N/A"
            else:
                size_c = os.path.getsize(out_c)
                meta_c = get_detailed_meta(out_c)
                info_c = f"{meta_c['dimensions']} {meta_c['process']} ({meta_c['bits']}b)"
                
                c_decomp_t, c_scans = get_djpeg_perf(out_c)
                decomp_c_str = f"{c_decomp_t} ({c_scans})" if c_decomp_t != "-" else f"({c_scans})"
                c_tj_fps, c_tj_mp = get_tjbench_perf(out_c)
                
                v_rc, _, _ = run_command(["magick", "compare", "-metric", "AE", img, out_c, "null:"])
                if v_rc == 0 or v_rc == 1:
                    c_diff = size_c - orig_size
                    if c_diff < 0:
                        c_delta_report = f"{c_diff} (WIN 🔥)" if (isinstance(sizes["perl"], int) and size_c < sizes["perl"]) else f"{c_diff} (WIN)"
                    elif c_diff > 0:
                        c_delta_report = f"+{c_diff} (PROG)" if "arithmetic" in info_c.lower() and mode_flag == "prog" else f"+{c_diff} (LOSE)"
                    else:
                        c_delta_report = "0 (PARITY)"
                        
                    # METADATA LAYER MD5 BIT-ACCURATE PARITY IDENTITY REPORTING
                    if label == "C Prog-Parity" and os.path.exists(cached_perl):
                        import hashlib
                        def get_md5(fpath):
                            h = hashlib.md5()
                            with open(fpath, "rb") as f:
                                for chunk in iter(lambda: f.read(65536), b""):
                                    h.update(chunk)
                            return h.hexdigest()
                        
                        # Clear up the text confusion: enforce the explicit bit-parity label
                        if get_md5(cached_perl) == get_md5(out_c):
                            c_delta_report = "🔥 BIT PARITY 🔥"
                else:
                    c_delta_report = "[CORRUPT] ❌"
                    
            if BENCHMARK_MODE:
                print(f"  {label:<13} | {info_c:<22} | {size_c:<8} | {time_c_str:<8} | {decomp_c_str:<18} | {c_tj_fps:<13} | {c_tj_mp:<13} | {c_delta_report:<14}")
            else:
                print(f"  {label:<13} | {info_c:<22} | {size_c:<8} | {time_c_str:<8} | {c_delta_report:<14}")

        print("-" * line_len)

if __name__ == "__main__":
    main()
