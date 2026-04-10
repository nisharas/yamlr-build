from __future__ import annotations
import logging
import os
from typing import Any, Dict, List
from pathlib import Path

logger = logging.getLogger("yamlr.engine.stages.ingest")

def execute_ingest_stage(engine: Any, content: str, relative_path: str, _config: Any) -> Dict[str, Any]:
    """
    Macro-Stage 1: Ingest (Lexical/Identity).
    
    Why: Handles text-to-shard translation and identity discovery.
    """
    from yamlr.parsers.lexer import YamlrLexer
    from yamlr.parsers.scanner import YamlrScanner
    
    lexer = YamlrLexer()
    scanner = YamlrScanner(engine.manager.catalog, app_name=engine.app_name)
    
    shards = lexer.shard(content)
    identities = scanner.scan_shards(shards)
    for ident in identities:
        ident.file_path = relative_path
        
    return {
        "shards": shards,
        "identities": identities,
        "findings": [] 
    }

def scan_file_identities(engine: Any, path: str) -> List[Any]:
    """Helper to scan a single file for identities with optimized fallbacks."""
    from yamlr.parsers.lexer import YamlrLexer
    from yamlr.parsers.scanner import YamlrScanner
    from yamlr.core.engine.models import ManifestIdentity

    try:
        content = engine.fs.read_text(Path(path))
        # 1. Try Native Fast Path
        if os.getenv("YAMLR_DISABLE_NATIVE") != "1":
            try:
                from yamlr_native import native_extract_metadata
                raw_meta = native_extract_metadata(content)
                if raw_meta:
                    results = []
                    for doc in raw_meta:
                        results.append(
                            ManifestIdentity(
                                kind=doc.get("kind"),
                                api_version=doc.get("apiVersion"),
                                name=doc.get("metadata", {}).get("name"),
                                namespace=doc.get("metadata", {}).get("namespace"),
                                labels=doc.get("metadata", {}).get("labels"),
                                file_path=path,
                            )
                        )
                    return results
            except (ImportError, RuntimeError, AttributeError):
                pass

        # 2. Fallback to Python Parser
        lexer = YamlrLexer()
        scanner = YamlrScanner(engine.manager.catalog, app_name=engine.app_name)
        shards = lexer.shard(content)
        ids = scanner.scan_shards(shards)
        for ident in ids:
            ident.file_path = path
        return ids
    except Exception as e:
        logger.debug(f"Identity scan failed for {path}: {e}")
        return []
