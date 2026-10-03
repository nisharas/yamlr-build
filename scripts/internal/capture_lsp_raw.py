import os
import subprocess

binary_path = os.path.abspath("vscode/bin/yamlr.exe")
process = subprocess.Popen(
    [binary_path, "lsp"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

msg = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {"processId": os.getpid(), "rootUri": "file:///d:/yamlr", "capabilities": {}},
    "id": 1,
}
import json

body = json.dumps(msg)
full_msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
process.stdin.write(full_msg.encode("utf-8"))
process.stdin.flush()

# Read the first response
line1 = process.stdout.readline()
line2 = process.stdout.readline()
line3 = process.stdout.readline()

# Write everything to a file for investigation
with open("lsp_debug_raw.txt", "wb") as f:
    f.write(line1)
    f.write(line2)
    f.write(line3)
    if b"Content-Length:" in line1:
        length = int(line1.split(b":")[1].strip())
        body = process.stdout.read(length)
        f.write(body)

process.terminate()
