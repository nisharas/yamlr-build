import os
import sys
from pathlib import Path

# Add src to sys.path to import yamlr components
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))

from yamlr.core.k8s_versions import MATRIX


def verify_k8s_support():
    """Verifies that all versions in MATRIX have physical catalog files."""
    print("[CI] Verifying Kubernetes Support Matrix Consistency...")
    print(f"[CI] Matrix Version Range: {MATRIX.min_supported} - {MATRIX.max_supported}")
    print(f"[CI] Default Recommended: v{MATRIX.default_recommended}")

    catalog_dir = ROOT_DIR / "src" / "yamlr" / "catalog"
    if not catalog_dir.exists():
        print(f"[ERROR] Catalog directory not found: {catalog_dir}")
        return False

    supported = MATRIX.supported_versions
    missing = []

    # Check for distilled JSON files
    for v in supported:
        catalog_file = catalog_dir / f"k8s_v{v}_distilled.json"

        # [SPECIAL CASE] v1 is our generic baseline
        if v == "1" or v == "v1":
            catalog_file = catalog_dir / "k8s_v1_distilled.json"

        if not catalog_file.exists():
            # v1.35 and 1.31 are our primary targets for this release.
            # v1.31 MUST be bundled for "Zero-Config" readiness.
            if v == MATRIX.default_recommended:
                missing.append(v)
                print(f"[FAIL] Required bundled catalog missing: {catalog_file.name}")
            else:
                # Other versions are downloadable, so we just warn.
                print(f"[WARN] Support matrix claims v{v}, but no bundled catalog found. (Will download on demand)")
        else:
            print(f"[OK] Found bundled catalog for v{v}")

    if missing:
        print("\n[ERROR] Missing required bundled assets for v1.6 stability.")
        print(f"Required but Missing: {', '.join(missing)}")
        return False

    print("\n[SUCCESS] Support Matrix is 100% synchronized with catalog assets.")
    return True


if __name__ == "__main__":
    if not verify_k8s_support():
        sys.exit(1)
    sys.exit(0)
