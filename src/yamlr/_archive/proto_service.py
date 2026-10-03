"""In-memory service adapter matching the yamlr.v1.ManifestService Protobuf specification.

Enables cloud-agnostic platforms (Backstage IDPs, ArgoCD/Flux controllers, Jenkins, GitLab)
to execute in-memory manifest scanning and healing without filesystem I/O overhead.
"""
import time
from typing import Any, Dict, List

import yamlr_native


class ManifestService:
    """Cloud-agnostic in-memory service implementation for manifest quality."""

    def __init__(self, default_k8s_version: str = "1.30"):
        self.default_k8s_version = default_k8s_version
        self._schemas_cache: Dict[str, Any] = {}

    def _get_schemas(self, version: str):
        if version not in self._schemas_cache:
            self._schemas_cache[version] = yamlr_native.native_get_schema_for_version(version)
        return self._schemas_cache[version]

    def scan_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Scans a manifest string in-memory according to ScanDocumentRequest."""
        start_time = time.perf_counter()
        content = request.get("content", "")
        _file_path = request.get("file_path", "in-memory.yaml")
        k8s_ver = request.get("target_k8s_version") or self.default_k8s_version

        schemas = self._get_schemas(k8s_ver)
        shards = yamlr_native.native_shard(content)

        violations_out: List[Dict[str, Any]] = []

        if shards:
            manifest = yamlr_native.native_structurize(shards)
            schema_violations = yamlr_native.native_check_schema_violations(content, schemas)
            for v in schema_violations:
                violations_out.append({
                    "rule_id": "SCH-001",
                    "check_type": "schema",
                    "severity": getattr(v, "severity", "error"),
                    "message": getattr(v, "message", str(v)),
                    "field_path": getattr(v, "field_path", ""),
                    "line_number": 1,
                    "help_uri": "https://yamlr.dev/errors/sch-001",
                })

            for iv in getattr(manifest, "integrity_violations", []):
                violations_out.append({
                    "rule_id": getattr(iv, "rule_id", "INT-001"),
                    "check_type": "integrity",
                    "severity": getattr(iv, "severity", "warning").lower(),
                    "message": getattr(iv, "message", str(iv)),
                    "field_path": "",
                    "line_number": 1,
                    "help_uri": f"https://yamlr.dev/errors/{getattr(iv, 'rule_id', 'int-001').lower()}",
                })

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "status": "passed" if not violations_out else "failed",
            "total_violations": len(violations_out),
            "violations": violations_out,
            "health_score": 100.0 if not violations_out else max(0.0, 100.0 - len(violations_out) * 10.0),
            "duration_ms": duration_ms,
        }

    def heal_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Heals a manifest string in-memory according to HealDocumentRequest."""
        start_time = time.perf_counter()
        content = request.get("content", "")
        _dry_run = request.get("dry_run", True)

        shards = yamlr_native.native_shard(content)
        if not shards:
            return {
                "healed_content": content,
                "mutated": False,
                "applied_fixes": [],
                "unified_diff": "",
                "duration_ms": 0,
            }

        healed = yamlr_native.native_reconstruct_yaml(shards)
        mutated = (healed != content)

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "healed_content": healed,
            "mutated": mutated,
            "applied_fixes": [],
            "unified_diff": "" if not mutated else "--- original\n+++ healed\n",
            "duration_ms": duration_ms,
        }
