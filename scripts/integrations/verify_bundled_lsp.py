import json
import os
import subprocess
import sys
import time


def send_rpc(proc, method, params, id=None):
    msg = {"jsonrpc": "2.0", "method": method, "params": params}
    if id is not None:
        msg["id"] = id

    body = json.dumps(msg)
    full_msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
    proc.stdin.write(full_msg.encode("utf-8"))
    proc.stdin.flush()


def read_rpc(proc, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        line = line.decode("utf-8")
        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            # Read until the empty line separating headers from body
            while True:
                h_line = proc.stdout.readline().decode("utf-8").strip()
                if not h_line:
                    break
            body = proc.stdout.read(length)
            raw = body.decode("utf-8")
            print(f"DEBUG RAW JSON: {raw}")
            return json.loads(raw)
    return None


def verify_bundled_lsp():
    binary_path = os.path.abspath("dist/yamlr.exe")
    if not os.path.exists(binary_path):
        print(f"❌ Binary not found at {binary_path}")
        return False

    print(f" Testing Bundled LSP: {binary_path}")
    process = subprocess.Popen(
        [binary_path, "lsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=".", bufsize=0
    )

    try:

        def listen_stderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                print(f"Server Log: {line.decode().strip()}", file=sys.stderr)

        import threading

        threading.Thread(target=listen_stderr, daemon=True).start()

        # 1. Initialize
        print("Sending LSP initialize...")
        send_rpc(
            process, "initialize", {"processId": os.getpid(), "rootUri": "file:///d:/yamlr", "capabilities": {}}, id=1
        )

        resp = read_rpc(process, timeout=10)
        if not resp:
            print(f"❌ No response from LSP server. Stderr: {process.stderr.read().decode('utf-8')}")
            return False

        if "result" not in resp:
            print(f"❌ Failed to initialize. Response: {resp}")
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
        # Filter through any other messages (like logs)
        print("Waiting for diagnostics...")
        for _ in range(5):
            diag_resp = read_rpc(process, timeout=5)
            if diag_resp and diag_resp.get("method") == "textDocument/publishDiagnostics":
                diags = diag_resp["params"]["diagnostics"]
                print(f"✅ LSP Diagnostics received: {len(diags)} issues found.")
                for d in diags:
                    print(f"  - [{d['severity']}] {d['message'].split('\n')[0]}")
                return True
            elif diag_resp:
                print(f"  (Ignored method: {diag_resp.get('method')})")

        print("❌ No diagnostics received.")
        return False

    finally:
        process.terminate()


if __name__ == "__main__":
    if verify_bundled_lsp():
        print("\n BUNDLED LSP IS FULLY OPERATIONAL.")
        sys.exit(0)
    else:
        sys.exit(1)
