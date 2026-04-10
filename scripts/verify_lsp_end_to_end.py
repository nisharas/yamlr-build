import json
import os
import subprocess
import time


def send_rpc(proc, method, params, id=None):
    msg = {"jsonrpc": "2.0", "method": method, "params": params}
    if id is not None:
        msg["id"] = id

    body = json.dumps(msg)
    full_msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
    proc.stdin.write(full_msg)
    proc.stdin.flush()


def read_rpc(proc, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            proc.stdout.readline()  # \r\n
            body = proc.stdout.read(length)
            return json.loads(body)
    return None


def verify_lsp_flow():
    # Start the LSP server
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    process = subprocess.Popen(
        ["python", "-m", "yamlr.cli.main", "lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=".",
    )

    try:
        # 1. Initialize
        print("Sending LSP initialize...")
        send_rpc(
            process, "initialize", {"processId": os.getpid(), "rootUri": "file:///d:/yamlr", "capabilities": {}}, id=1
        )

        resp = read_rpc(process)
        if not resp or "result" not in resp:
            print(f"Failed to initialize. Stderr: {process.stderr.read()}")
            return False
        print("✅ LSP Handshake: Initialized")

        # 2. Open a "bad" file
        print("Sending textDocument/didOpen with a bad manifest...")
        bad_manifest = """
apiVersion: v1
kind: Pod
metadata:
  name: insecure-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
    securityContext:
      privileged: true
"""
        send_rpc(
            process,
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": "file:///d:/yamlr/test-lsp.yaml",
                    "languageId": "yaml",
                    "version": 1,
                    "text": bad_manifest,
                }
            },
        )

        # 3. Wait for diagnostics
        # Diagnostics are notifications (no id)
        diag_resp = read_rpc(process, timeout=10)
        if diag_resp and diag_resp.get("method") == "textDocument/publishDiagnostics":
            diags = diag_resp["params"]["diagnostics"]
            print(f"✅ LSP Diagnostics received: {len(diags)} issues found.")
            for d in diags:
                print(f"  - [{d['severity']}] {d['message'].split('\n')[0]}")
            return True
        else:
            print("❌ No diagnostics received.")
            return False

    finally:
        process.terminate()


if __name__ == "__main__":
    if verify_lsp_flow():
        print("\n🏆 VS Code Extension Backend (LSP) is FULLY OPERATIONAL.")
        exit(0)
    else:
        exit(1)
