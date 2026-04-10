from __future__ import annotations

import os
import subprocess
import sys


def main():
    """
    Mimics the future Rust scanner entry point.
    For now, it simply wraps the Python engine to verify the Parity Guard infrastructure.
    """
    # In the future, this would be a path to yamlr.exe
    # For testing the 'Shadow Rollout' logic, we just use the current python engine.

    # Ensure PYTHONPATH is set so it can find the yamlr package if running from here
    env = os.environ.copy()
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = os.path.join(os.getcwd(), "src")

    cmd = [sys.executable, "-m", "yamlr", "scan"] + sys.argv[1:]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    # Pass through stdout and stderr
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
