from __future__ import annotations

import os

files = [
    r"D:\yamlr\tests\stubs\rust_scanner_stub.py",
    r"D:\yamlr\scripts\benchmark.py",
    r"D:\yamlr\scripts\build_nuitka.py",
    r"D:\yamlr\scripts\verify_argo.py",
    r"D:\yamlr\scripts\verify_flux.py",
    r"D:\yamlr\scripts\verify_hyperscale.py",
    r"D:\yamlr\scripts\verify_shield_final.py",
    r"D:\yamlr\scripts\verify_shield.py",
    r"D:\yamlr\hack\build_binaries.py",
    r"D:\yamlr\hack\build.py",
    r"D:\yamlr\hack\push_all.py",
    r"D:\yamlr\hack\smoke_test_semantic.py",
    r"D:\yamlr\hack\verify_binary.py",
    r"D:\yamlr\scripts\compute_metrics.py",
    r"D:\yamlr\scripts\fuzz_lexer.py",
    r"D:\yamlr\scripts\package.py",
    r"D:\yamlr\scripts\sync_actions.py",
]

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "from __future__ import annotations" not in content:
            new_content = "from __future__ import annotations\n" + content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Updated {file_path}")
