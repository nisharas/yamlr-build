import os
import re

# Mapping of legacy/ghost paths to definitive physical locations
PATH_MAP = {
    r'(?<!src/yamlr/)parsers/lexer\.py': 'src/yamlr/parsers/lexer.py',
    r'(?<!src/yamlr/)parsers/scanner\.py': 'src/yamlr/parsers/scanner.py',
    r'(?<!src/yamlr/)parsers/structurer\.py': 'src/yamlr/parsers/structurer.py',
    r'(?<!src/yamlr/)parsers/schema_healer\.py': 'src/yamlr/parsers/schema_healer.py',
    r'(?<!src/yamlr/)parsers/migrator\.py': 'src/yamlr/core/migrator.py',
    r'(?<!src/yamlr/core/)analyzers/auditor\.py': 'src/yamlr/core/engine/auditor.py',
    r'(?<!src/yamlr/core/)analyzers/cross_resource\.py': 'src/yamlr/analyzers/cross_resource.py',
    r'(?<!src/yamlr/core/)analyzers/security\.py': 'src/yamlr/analyzers/security.py',
    r'(?<!src/yamlr/core/)analyzers/best_practices\.py': 'src/yamlr/analyzers/best_practices.py',
    r'src/yamlr/core/pipeline\.py': 'src/yamlr/core/engine/base.py',
    r'src/yamlr/core/lexer\.py': 'src/yamlr/parsers/lexer.py',
    r'src/yamlr/pro/opa_adapter\.py': 'src/yamlr/pro/bridge.py',
    r'scripts/verify_argo\.py': 'scripts/verify_lsp_end_to_end.py',
    r'scripts/verify_flux\.py': 'scripts/verify_lsp_end_to_end.py',
    r'scripts/catalog_pipeline\.py': 'scripts/catalog_distiller.py',
}

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        original_content = content
        for pattern, replacement in PATH_MAP.items():
            content = re.sub(pattern, replacement, content)

        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"FIXED: {filepath}")
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")

def main():
    scan_dirs = ["docs", "src", "scripts", "website/docs"]
    for d in scan_dirs:
        if not os.path.exists(d): continue
        for root, dirs, files in os.walk(d):
            # Exclude node_modules, .git
            if any(x in root for x in ["node_modules", ".git"]): continue
            for file in files:
                if file.endswith('.md') or file.endswith('.py'):
                    fix_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
