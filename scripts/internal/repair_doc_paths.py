import os
import re

def repair_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        orig = content
        # 1. Standardize core/analyzers/ to analyzers/ (since analyzers is root-level in src/yamlr)
        # Wait, I found auditor.py is in core/engine.

        # Mapping rules based on physical truth:
        REPLACEMENTS = [
            ('src/yamlr/core/engine/auditor.py', 'src/yamlr/core/engine/auditor.py'),
            ('src/yamlr/analyzers/base.py', 'src/yamlr/analyzers/base.py'),
            ('src/yamlr/core/engine/auditor.py', 'src/yamlr/core/engine/auditor.py'),
            ('src/yamlr/analyzers/base.py', 'src/yamlr/analyzers/base.py'),
            ('src/yamlr/core/engine/auditor.py', 'src/yamlr/core/engine/auditor.py'),
        ]

        for old, new in REPLACEMENTS:
            content = content.replace(old, new)

        # Idempotency: avoid double-prefix src/yamlr/
        content = content.replace('src/yamlr/', 'src/yamlr/')

        if content != orig:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"REPAIRED: {filepath}")
    except Exception as e:
        print(f"Error repairing {filepath}: {e}")

def main():
    scan_dirs = ["docs", "src", "scripts", "website/docs"]
    for d in scan_dirs:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            if any(x in root for x in [".git", "node_modules"]): continue
            for file in files:
                if file.endswith(('.md', '.py', '.yaml')):
                    repair_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
