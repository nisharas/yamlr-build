from __future__ import annotations
import os
import subprocess
import sys


def main():
    print("📦 Yamlr Binary Builder (Universal Edition)")

    # 1. Check for Nuitka (The "Pro" Choice)
    use_nuitka = False
    try:
        subprocess.check_output([sys.executable, "-m", "nuitka", "--version"], stderr=subprocess.STDOUT)
        use_nuitka = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Nuitka module not found via 'python -m nuitka'. Checking system path...")
        try:
            # [Security] Remove shell=True to prevent metacharacter injection
            subprocess.check_output(["nuitka", "--version"], stderr=subprocess.STDOUT)
            use_nuitka = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Nuitka not found. Falling back to PyInstaller.")

    # 2. Configure Paths
    base_dir = os.path.abspath(os.curdir)
    src_data = os.path.join(base_dir, "src", "yamlr", "core", "data")
    catalog_dir = os.path.abspath("catalog")
    
    # Destination inside the bundle must match package structure
    dst_data = os.path.join("yamlr", "core", "data")
    dst_catalog = os.path.join("Yamlr", "catalog")

    worker_name = "yamlr-worker"
    entry_point = os.path.join("src", "yamlr", "__main__.py")

    if use_nuitka:
        print("🚀 Compiling with Nuitka (Standalone + LTO + Brutal Pruning)...")
        cmd = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            f"--output-filename={worker_name}.exe" if os.name == "nt" else f"--output-filename={worker_name}",
            "--remove-output",
            "--assume-yes-for-downloads",
            f"--include-data-dir={src_data}={dst_data}",
            f"--include-data-dir={catalog_dir}={dst_catalog}",
            "--lto=yes", # Link Time Optimization for smaller/faster binary
            "--enable-plugin=anti-bloat",
            "--include-package=importlib",
            # Brutal Exclusions
            "--nofollow-import-to=numpy",
            "--nofollow-import-to=scipy",
            "--nofollow-import-to=pygments",
            "--nofollow-import-to=matplotlib",
            "--nofollow-import-to=tkinter",
            "--nofollow-import-to=unittest",
            "--nofollow-import-to=test",
            "--nofollow-import-to=idlelib",
            entry_point
        ]
    else:
        # PyInstaller Fallback
        # ... (unchanged)
        pass

    print(f"🔨 Executing: {' '.join(cmd)}")

    try:
        subprocess.check_call(cmd)
        print("\n✅ Build Successful!")
        
        # 4. Packaging (Zero-PIP Size Optimization)
        # Why: We use Zstandard Level 22 + Tar for the ultimate compression.
        if use_nuitka:
            import tarfile
            import zstandard as zstd
            dist_dir = "__main__.dist" # Nuitka default
            zst_name = "yamlr-worker.tar.zst"
            print(f"🤐 Compressing {dist_dir} -> {zst_name} (Zstd Level 22)...")
            
            cctx = zstd.ZstdCompressor(level=22)
            with open(zst_name, 'wb') as f:
                with cctx.stream_writer(f) as compressor:
                    with tarfile.open(fileobj=compressor, mode='w|') as tar:
                        tar.add(dist_dir, arcname='.')
            
            print(f"📊 Zst size: {os.path.getsize(zst_name) / 1024 / 1024:.2f} MB")
        else:
            # ... (unchanged)
            pass
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
