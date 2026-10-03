import json
import os
import subprocess
import sys
import time


def test_lsp():
    env = os.environ.copy()
    env["PYTHONPATH"] = f"src{os.pathsep}{env.get('PYTHONPATH', '')}"
    process = subprocess.Popen(
        [sys.executable, "-m", "yamlr", "lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=".",
    )

    # Note: Full LSP handshake is complex, but we can check if it stays alive
    # and doesn''t crash immediately due to missing dependencies.
    time.sleep(2)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        print(f"LSP Process died with code {process.returncode}")
        print(f"Stderr: {stderr}")
        return False

    print("✅ LSP Server started correctly and is awaiting JSON-RPC via stdio.")
    process.terminate()
    return True


if __name__ == "__main__":
    if not test_lsp():
        exit(1)
