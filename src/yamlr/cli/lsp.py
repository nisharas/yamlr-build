#!/usr/bin/env python3
"""
Yamlr Sovereign LSP Entrypoint
-------------------------------
Why: Dedicated, side-effect-free entrypoint for the VS Code extension.
     Ensures 100% protocol integrity by bypassing global stdout redirection
     and forcing sequential execution to prevent native Windows deadlocks.
"""

import multiprocessing
import os
import sys


def main():
    """LSP Entrypoint Dispatcher.
    
    Why: Separates the compiled engine from the uncompiled protocol proxy.
    """
    # 🛡️ MANDATORY: Freeze support for native binaries
    multiprocessing.freeze_support()

    # If running as a compiled binary, we MUST use the external proxy
    if getattr(sys, "frozen", False):
        import subprocess
        
        # Look for the proxy script in the same directory or package
        proxy_script = os.path.join(os.path.dirname(sys.executable), "lsp_proxy.py")
        if not os.path.exists(proxy_script):
            # Fallback to searching the source tree if bundled as data
            proxy_script = os.path.join(os.path.dirname(__file__), "lsp_proxy.py")

        if os.path.exists(proxy_script):
            # Launch the proxy using the system python
            # Note: The proxy will then call THIS binary back for analysis
            try:
                # We use 'python' assuming it's in the PATH for the LSP environment
                cmd = ["python", proxy_script]
                os.environ["YAMLR_BINARY_PATH"] = sys.executable
                subprocess.run(cmd)
                sys.exit(0)
            except Exception as e:
                sys.stderr.write(f"❌ Failed to launch LSP Proxy: {e}\n")
                sys.stderr.write("Ensure 'python', 'pygls', and 'lsprotocol' are installed.\n")
                sys.exit(1)
        else:
            sys.stderr.write("❌ LSP Proxy script not found. LSP mode is only available in the full distribution.\n")
            sys.exit(1)

    # Development Mode: Fallback to direct start if available
    try:
        from yamlr.cli.lsp_proxy import start_lsp
        start_lsp()
    except ImportError:
        sys.stderr.write("❌ LSP dependencies missing. Run: pip install pygls lsprotocol\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
