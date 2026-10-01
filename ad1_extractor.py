#!/usr/bin/env python3
"""
AD1-Bridge Extractor Engine
Automates extraction of AccessData AD1 images with metadata preservation.
Supports bundled native fast binaries with seamless fallback to pure Python.
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_native_binary():
    """Finds the bundled standalone native binary if compatible."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux" and machine in ("x86_64", "amd64"):
        bundled = os.path.join(SCRIPT_DIR, "bin", "linux_x86_64", "ad1extract")
        if os.path.isfile(bundled) and os.access(bundled, os.X_OK):
            return bundled

    if system == "windows":
        bundled = os.path.join(SCRIPT_DIR, "bin", "windows_x64", "ad1extract.exe")
        if os.path.isfile(bundled):
            return bundled

    # Check system PATH
    import shutil
    path_bin = shutil.which("ad1extract")
    if path_bin:
        return path_bin

    return None


def extract_with_native(binary_path, ad1_path, output_dir, verbose=False):
    """Executes the native C-based ad1extract tool with progress reporting."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [binary_path, "-m", "-d", output_dir, "-i", ad1_path]
    if verbose:
        print(f"[+] Executing native engine: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )

    for line in iter(process.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue
        if verbose:
            print(f"[ENGINE] {line}")
        else:
            # Emit short progress hints for Autopsy
            if "Extracting" in line or "finished" in line.lower():
                print(f"[STATUS] {line}")

    process.stdout.close()
    return process.wait()


def sanitize_filename(name):
    """Sanitizes names containing forbidden filesystem characters like colons."""
    # Replace colons and control characters for cross-platform compatibility
    cleaned = name.replace(":", "_").replace("<", "_").replace(">", "_")
    cleaned = cleaned.replace('"', "_").replace("|", "_").replace("?", "_").replace("*", "_")
    return cleaned


def extract_with_python(ad1_path, output_dir, verbose=False):
    """Pure Python fallback extractor using ad1_core."""
    from ad1_core.parser import AD1

    print("[+] Using Pure Python 3 extraction engine...")
    with AD1(ad1_path) as img:
        total_extracted = 0

        def extract_node(node, current_out_dir):
            nonlocal total_extracted
            safe_name = sanitize_filename(node.name)
            target_path = os.path.join(current_out_dir, safe_name)

            if node.is_dir:
                os.makedirs(target_path, exist_ok=True)
                for child in node.children:
                    extract_node(child, target_path)
            else:
                try:
                    data = img.read_file(node)
                    with open(target_path, "wb") as f:
                        f.write(data)
                    total_extracted += 1

                    # Apply timestamps if present
                    meta = img.metadata(node)
                    # 9 = modified time (ISO: YYYYMMDDTHHMMSS)
                    mtime_str = meta.get(9)
                    if mtime_str:
                        try:
                            # Sample: 20210430T012023.828110
                            clean_time = mtime_str.split(".")[0]
                            dt = datetime.strptime(clean_time, "%Y%m%dT%H%M%S")
                            epoch = dt.timestamp()
                            os.utime(target_path, (epoch, epoch))
                        except Exception:
                            pass

                    if verbose or total_extracted % 25 == 0:
                        print(f"[STATUS] Extracted {total_extracted} files... ({safe_name})")
                except Exception as e:
                    if verbose:
                        print(f"[-] Warning: Failed to extract {node.name}: {e}")

        # Start extraction from root children
        for child in img.root.children:
            extract_node(child, output_dir)

    print(f"[+] Python extraction complete: {total_extracted} files extracted.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="AD1-Bridge Extractor Engine")
    parser.add_argument("-i", "--input", required=True, help="Input .ad1 file")
    parser.add_argument("-o", "--output", required=True, help="Output destination folder")
    parser.add_argument("--engine", choices=["auto", "native", "python"], default="auto", help="Engine selection")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[-] Error: Input file '{args.input}' not found.", file=sys.stderr)
        sys.exit(1)

    ad1_abs = os.path.abspath(args.input)
    out_abs = os.path.abspath(args.output)
    os.makedirs(out_abs, exist_ok=True)

    print(f"[*] AD1-Bridge Starting...")
    print(f"[*] Input AD1: {ad1_abs}")
    print(f"[*] Output Dir: {out_abs}")

    start_time = time.time()
    rc = 1

    native_bin = get_native_binary()

    if args.engine == "native" or (args.engine == "auto" and native_bin):
        if native_bin:
            print(f"[*] Active Engine: Native Fast Binary ({os.path.basename(native_bin)})")
            rc = extract_with_native(native_bin, ad1_abs, out_abs, args.verbose)
        else:
            print("[-] Native binary not found. Falling back to Python engine...")
            rc = extract_with_python(ad1_abs, out_abs, args.verbose)
    else:
        rc = extract_with_python(ad1_abs, out_abs, args.verbose)

    duration = time.time() - start_time
    if rc == 0:
        print(f"[+] Extraction finished successfully in {duration:.2f} seconds.")
    else:
        print(f"[-] Extraction exited with code {rc}.", file=sys.stderr)

    sys.exit(rc)


if __name__ == "__main__":
    main()
