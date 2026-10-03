import subprocess
import os
import sys
import shutil
import platform
import zipfile
import tarfile

# Calculate base directory (Project Root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NATIVE_CORE_DIR = os.path.join(BASE_DIR, "native_core")
WEBSITE_WASM_DIR = os.path.join(BASE_DIR, "website", "public", "wasm")
DIST_DIR = os.path.join(BASE_DIR, "dist")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

def build_man_pages():
    print("[!] Generating Man Pages...")
    try:
        script_path = os.path.join(DOCS_DIR, "scripts", "generate_man_pages.py")
        subprocess.run([sys.executable, script_path], check=True)
        print("[OK] Man Pages generated.")
    except Exception as e:
        print(f"[WARNING] Man page generation failed: {e}")

def build_python_extension():
    print(f"[!] Building Python Native Extension (PyO3) in {NATIVE_CORE_DIR}...")
    try:
        # Use --user to avoid WinError 5 Access Denied on global site-packages
        # Use sys.executable -m pip to ensure we use the active environment
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "."], cwd=NATIVE_CORE_DIR, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[bold red][ERROR][/bold red] Native build failed: {e}")
        print("[dim]Tip: Ensure no other Yamlr processes are running that might lock the .pyd file.[/dim]")
        sys.exit(1)

def build_wasm_core():
    print("[!] Building WASM Core (wasm-pack)...")
    try:
        if not os.path.exists(WEBSITE_WASM_DIR):
            os.makedirs(WEBSITE_WASM_DIR)
        
        subprocess.run([
            "wasm-pack", "build", 
            "--target", "web", 
            "--out-dir", WEBSITE_WASM_DIR
        ], cwd=NATIVE_CORE_DIR, check=True)
        print(f"[OK] WASM Core built and synced to {WEBSITE_WASM_DIR}")
    except Exception as e:
        print(f"[WARNING] WASM build failed (wasm-pack might not be installed): {e}")

def create_standalone_binary():
    print("[!] Packaging Standalone Binary (Nuitka)...")
    try:
        # Clean previous dist to avoid confusion
        if os.path.exists(DIST_DIR):
            import shutil
            shutil.rmtree(DIST_DIR)
        os.makedirs(DIST_DIR)
            
        # Engine Standard: Use PYTHONPATH to help Nuitka find the 'src' layout
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.join(BASE_DIR, "src")
        
        # We use --standalone for reliability on Windows. 
        # --onefile is often flagged by AV.
        subprocess.run([
            sys.executable, "-m", "nuitka", 
            "--standalone", 
            "--include-package=yamlr",
            "--include-package=yamlr_native",
            "--include-package=rich",
            "--output-dir=" + DIST_DIR,
            "--output-filename=yamlr.exe",
            os.path.join(BASE_DIR, "src", "yamlr", "cli", "main.py")
        ], env=env, check=True)
        
        # Nuitka creates 'yamlr.dist' inside DIST_DIR when -o yamlr.exe is used with --standalone
        # We want the contents of 'yamlr.dist' to be the final distribution.
        print(f"[OK] Standalone distribution created in {DIST_DIR}/yamlr.dist")
    except Exception as e:
        print(f"[ERROR] Binary packaging failed: {e}")

def _get_dist_items(os_name):
    """Generates the manifest of items to include in the distribution."""
    # In standalone mode, Nuitka creates a .dist folder based on the script name (main.py)
    standalone_dir = os.path.join(DIST_DIR, "main.dist")
    
    items = [
        # Include the entire standalone directory contents
        (standalone_dir, "bin"),
        (os.path.join(DOCS_DIR, "man", "man1"), "man/man1"),
        (os.path.join(BASE_DIR, "README.md"), "README.md"),
    ]
    license_path = os.path.join(BASE_DIR, "LICENSE")
    if os.path.exists(license_path):
        items.append((license_path, "LICENSE"))
    return items

def _pack_zip(archive_path, items):
    """Creates a ZIP archive for Windows distributions."""
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for src, arc in items:
            if os.path.isdir(src):
                for root, _, files in os.walk(src):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, src)
                        zf.write(full_path, os.path.join(arc, rel_path))
            else:
                zf.write(src, arc)

def _pack_tar(archive_path, items):
    """Creates a TAR.GZ archive for Unix distributions."""
    with tarfile.open(archive_path, "w:gz") as tf:
        for src, arc in items:
            tf.add(src, arcname=arc)

def create_distribution_archives():
    """Orchestrates the creation of platform-specific distribution archives."""
    print("\n[!] Creating Distribution Archives...")
    try:
        os_name = platform.system().lower()
        machine = platform.machine().lower()
        base_name = f"yamlr-0.1.0-{os_name}-{machine}"
        items = _get_dist_items(os_name)

        if os_name == "windows":
            path = os.path.join(DIST_DIR, f"{base_name}.zip")
            _pack_zip(path, items)
            print(f"[OK] ZIP archive created: {path}")
        else:
            path = os.path.join(DIST_DIR, f"{base_name}.tar.gz")
            _pack_tar(path, items)
            print(f"[OK] TAR.GZ archive created: {path}")
    except Exception as e:
        print(f"[ERROR] Archive creation failed: {e}")

def run_all():
    """Executes the full Build Pipeline with path-independence."""
    print(f"--- Yamlr Build Pipeline (Root: {BASE_DIR}) ---")
    build_python_extension()
    build_man_pages()
    build_wasm_core()
    create_standalone_binary()
    create_distribution_archives()
    print("\n--- Build Complete: Yamlr v0.1.0 (Alpha) ---")

if __name__ == "__main__":
    run_all()
