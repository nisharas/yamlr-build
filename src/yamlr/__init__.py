# Yamlr Namespace Initialization
import pkgutil
import sys
from pathlib import Path

# Enable "Namespace Packaging" so Yamlr Pro can merge into this folder
__path__ = pkgutil.extend_path(__path__, __name__)

# Nuitka/PyInstaller Path Anchor
if getattr(sys, "frozen", False):
    import os
    # For Nuitka onefile, os.path.dirname(__file__) is the internal directory
    bundle_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
