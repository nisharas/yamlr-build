"""Compatibility import for the packaged native Rust extension.

Maturin places the extension inside this package. Keep the public
``import yamlr_native`` API stable for the SDK and CLI bridge.
"""

from .yamlr_native import *  # noqa: F403
