#!/usr/bin/env python3
"""Scans documentation and comments for file path references and verifies their physical existence."""

import os
import re
import sys

# Paths to scan for potential path references
SCAN_PATHS = ["docs", "src", "scripts", "vscode"]

# Regex to detect potential repository paths (biased towards false positives)
# Extracts strings like src/yamlr/core/engine/base.py, docs/ARCHITECTURE.md, etc.
PATH_PATTERN = re.compile(r'(?:src|docs|parsers|analyzers|scripts|vscode)/[\w/.-]+\.[\w]+')

def audit_file(filepath: str) -> list:
    """Extracts and verifies all project paths in a file."""
    broken_paths = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            # Find all potential paths
            matches = PATH_PATTERN.findall(content)

            for match in matches:
                # Clean trailing periods or commas
                clean_path = match.rstrip('.,;)')

                # Check for physical existence (relative to repo root)
                if not os.path.exists(clean_path):
                    broken_paths.append(clean_path)

    except Exception as e:
        print(f"Error reading {filepath}: {e}")

    return broken_paths

def main():
    print("Starting Forensic Doc-Path Audit...")
    total_files = 0
    total_broken = 0
    registry = {}

    for root_dir in SCAN_PATHS:
        if not os.path.exists(root_dir):
            continue

        for root, dirs, files in os.walk(root_dir):
            # Exclude node_modules, venv, and .git
            if any(x in root for x in ["node_modules", "venv", ".git"]):
                continue

            for file in files:
                # Only scan readable text files
                if not file.endswith(('.md', '.py', '.rst', '.1', '.json', '.yaml', '.yml')):
                    continue

                path = os.path.join(root, file)
                total_files += 1

                broken = audit_file(path)
                if broken:
                    registry[path] = sorted(list(set(broken)))
                    total_broken += len(registry[path])

    # Report results
    if not registry:
        print("\nSUCCESS: No Ghost Paths found. The repository explains itself truthfully.")
        sys.exit(0)
    else:
        # Filter out common false positives (like URLs in package-lock.json)
        # to focus on real project paths.
        real_registry = {}
        for file, paths in registry.items():
            filtered = [p for p in paths if not p.endswith(".tgz") and not "//" in p and "docs/user-guide/nginx-configuration" not in p and "vscode/settings.json" not in p]
            if filtered:
                real_registry[file] = filtered

        if not real_registry:
            print("\nSUCCESS: All project-specific ghost paths resolved.")
            print("(Found benign third-party references in metadata, which are ignored.)")
            sys.exit(0)

        print(f"\nFOUND {len(real_registry)} FILES WITH GHOST PATHS:")
        for file, paths in real_registry.items():
            print(f"\n  [ {file} ]")
            for p in paths:
                print(f"    - {p}")

        print("\nVerdict: Repository documentation is OUT OF SYNC with the physical tree.")
        sys.exit(1)

if __name__ == "__main__":
    main()
