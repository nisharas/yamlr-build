import os
import re

# The absolute ground truth mapping based on the recursive walk
SYMMETRY_MAP = {
    # Parsers (src/yamlr/parsers/)
    r'(?<!src/yamlr/)parsers/lexer\.py': 'src/yamlr/parsers/lexer.py',
    r'(?<!src/yamlr/)parsers/scanner\.py': 'src/yamlr/parsers/scanner.py',
    r'(?<!src/yamlr/)parsers/structurer\.py': 'src/yamlr/parsers/structurer.py',
    r'(?<!src/yamlr/)parsers/schema_healer\.py': 'src/yamlr/parsers/schema_healer.py',
    r'(?<!src/yamlr/)parsers/migrator\.py': 'src/yamlr/core/migrator.py',
    r'(?<!src/yamlr/)parsers/physicist\.py': 'src/yamlr/parsers/physicist.py',

    # Analyzers (src/yamlr/analyzers/)
    r'(?<!src/yamlr/)analyzers/base\.py': 'src/yamlr/analyzers/base.py',
    r'(?<!src/yamlr/)analyzers/best_practices\.py': 'src/yamlr/analyzers/best_practices.py',
    r'(?<!src/yamlr/)analyzers/cross_resource\.py': 'src/yamlr/analyzers/cross_resource.py',
    r'(?<!src/yamlr/)analyzers/network_logic\.py': 'src/yamlr/analyzers/network_logic.py',
    r'(?<!src/yamlr/)analyzers/security\.py': 'src/yamlr/analyzers/security.py',

    # Engine & Orchestration (src/yamlr/core/engine/)
    r'(?<!src/yamlr/core/engine/)analyzers/auditor\.py': 'src/yamlr/core/engine/auditor.py',
    r'src/yamlr/analyzers/auditor\.py': 'src/yamlr/core/engine/auditor.py',
    r'src/yamlr/analyzers/': 'src/yamlr/analyzers/',
    r'src/yamlr/core/pipeline\.py': 'src/yamlr/core/engine/base.py',
    r'src/yamlr/pro/opa_adapter\.py': 'src/yamlr/pro/bridge.py',
}

def sync_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        orig = content

        # 1. First, resolve the double-prefixing messy paths
        content = content.replace('src/yamlr/', 'src/yamlr/')

        # 2. Iterate through mapping
        for pattern, replacement in SYMMETRY_MAP.items():
            content = re.sub(pattern, replacement, content)

        # 3. Handle double core/ segments (idempotency)
        content = content.replace('src/yamlr/core/', 'src/yamlr/core/')

        if content != orig:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"SYNCED: {filepath}")
    except Exception as e:
        print(f"Error syncing {filepath}: {e}")

def main():
    scan_dirs = ["docs", "src", "scripts", "website/docs"]
    for d in scan_dirs:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            if any(x in root for x in [".git", "node_modules"]): continue
            for file in files:
                if file.endswith(('.md', '.py', '.yaml')):
                    sync_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
