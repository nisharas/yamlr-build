"""Release packaging utility for Yamlr standalone native binaries.

Archives the compiled native executable, man pages, and license into
distribution tarballs / zip archives for GitHub Releases and package managers.
"""
import os
import platform
import shutil
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST_DIR = ROOT / "dist" / "binaries"


def package_release_binary(version: str = "0.1.0"):
    """Packages the compiled release binary into platform tarball / zip."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    system = platform.system().lower()
    machine = platform.machine().lower()

    if "arm" in machine or "aarch64" in machine:
        arch = "aarch64"
    else:
        arch = "x86_64"

    bin_name = "yamlr.exe" if system == "windows" else "yamlr"
    bin_path = ROOT / "native_core" / "target" / "release" / bin_name

    if not bin_path.exists():
        bin_path = ROOT / "native_core" / "target" / "debug" / bin_name

    if not bin_path.exists():
        raise FileNotFoundError(f"Native binary not found at {bin_path}. Run 'cargo build --release' first.")

    archive_base = f"yamlr-v{version}-{system}-{arch}"

    if system == "windows":
        zip_path = DIST_DIR / f"{archive_base}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bin_path, arcname=bin_name)
            license_file = ROOT / "LICENSE"
            if license_file.exists():
                zf.write(license_file, arcname="LICENSE")
        print(f"[PACKAGE] Generated Windows release zip: {zip_path}")
    else:
        tar_path = DIST_DIR / f"{archive_base}.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            tf.add(bin_path, arcname=bin_name)
            license_file = ROOT / "LICENSE"
            if license_file.exists():
                tf.add(license_file, arcname="LICENSE")
        print(f"[PACKAGE] Generated Unix release tarball: {tar_path}")


if __name__ == "__main__":
    package_release_binary()
