import json
import os
import subprocess
import sys
import time


def diagnose():
    binary_path = os.path.abspath("vscode/bin/yamlr.exe")
    print(f"🚀 [DIAGNOSTIC] Checking binary at: {binary_path}")

    if not os.path.exists(binary_path):
        print("❌ [ERROR] Binary not found!")
        return

    # Mock LSP Initialize Request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": os.getpid(), "rootUri": None, "capabilities": {}},
    }

    msg = json.dumps(init_request)
    header = f"Content-Length: {len(msg)}\r\n\r\n"
    full_payload = (header + msg).encode("utf-8")

    print("🛰️ [SYSTEM] Launching engine in LSP mode...")
    try:
        proc = subprocess.Popen(
            [binary_path, "lsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Send handshake
        print("🤝 [HANDSHAKE] Sending 'initialize' request...")
        proc.stdin.write(full_payload)
        proc.stdin.flush()

        # Give it a second to respond
        time.sleep(2)

        # Check stderr for pollution/errors
        print("🔍 [AUDIT] Checking stderr for pollution...")
        stderr_output = proc.stderr.read(1024).decode("utf-8")
        if stderr_output:
            print(f"📡 [STDERR] (Logs/Errors): {stderr_output}")

        # Check stdout for JSON-RPC response
        print("📥 [RESPONSE] Reading stdout...")
        stdout_output = proc.stdout.read(1024).decode("utf-8")

        if "jsonrpc" in stdout_output:
            print("✅ [SUCCESS] Binary responded with valid JSON-RPC!")
            print(f"📦 [DATA]: {stdout_output[:200]}...")
        else:
            print("❌ [FAILURE] No valid LSP response found in stdout.")
            print(f"🏜️ [STDOUT RAW]: {stdout_output}")

        proc.terminate()

    except Exception as e:
        print(f"🔥 [CRITICAL] Diagnostic Crashed: {e}")


if __name__ == "__main__":
    diagnose()
