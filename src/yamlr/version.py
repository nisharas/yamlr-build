"""Single source of truth version definition for yamlr (Python distribution)."""

import os

_version_file = os.path.join(os.path.dirname(__file__), "..", "..", "VERSION")
if os.path.isfile(_version_file):
    with open(_version_file, "r", encoding="utf-8") as _f:
        __version__ = _f.read().strip()
else:
    __version__ = "0.1.0"
