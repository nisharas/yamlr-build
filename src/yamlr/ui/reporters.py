"""
Yamlr REPORTERS
------------------
Structured output generators for CI/CD integration.
"""

from __future__ import annotations
import json
import time
from typing import Any, Dict

__all__ = ["JSONReporter", "SARIFReporter"]


class JSONReporter:
    """Generates a standard JSON report of the execution."""

    def generate(self, results: Dict[str, Any], duration: float, scout: bool = False, timing: Optional[Dict[str, Any]] = None) -> str:
        """Serializes the engine's execution results into a structured JSON report.
        
        Why: To provide a machine-readable audit trail for external tools and CI/CD pipelines.
        """
        processed = results.get("processed_files", [])

        # Sanitize results (remove internal keys starting with _)
        sanitized_results = []
        total_issues = 0
        for f in processed:
            # Flatten to dict based on object capability
            if hasattr(f, "to_dict"):
                data = f.to_dict()
            elif hasattr(f, "__dict__"):
                data = f.__dict__
            else:
                data = f
                
            clean_f = {k: v for k, v in data.items() if not k.startswith("_")}
            sanitized_results.append(clean_f)
            total_issues += len(data.get("findings", []))

        # [FREE-12-08] Enforce strict determinism for CI/CD consistency
        sanitized_results.sort(key=lambda x: x.get("file_path", ""))

        report = {
            "metadata": {
                "tool": "Yamlr",
                "version": "0.1.0",
                "timestamp": time.time(),
                "duration_seconds": duration,
                "performance_timing": timing,
            },
            "summary": {
                "total_files": len(processed),
                "healed_files": results.get("healed_count", 0),
                "total_issues": total_issues,
            },
            "results": sanitized_results,
        }

        if scout:
            # Filter results to strictly match Rust's scout-only structure
            scout_results = []
            for r in sanitized_results:
                scout_results.append({
                    "file_path": r.get("file_path"),
                    "full_path": r.get("full_path"),
                    "success": True,
                    "status": "UNCHANGED",
                    "kind": r.get("kind"),
                    "identities": r.get("identities", []),
                    "findings": [],
                    "dna_integrity_score": 100,
                    "timestamp": report["metadata"]["timestamp"],
                    "processing_time_seconds": 0.0,
                    "written": False,
                    "healed_content": r.get("healed_content")
                })
            report["results"] = scout_results
            report["summary"]["total_issues"] = 0
            report["summary"]["healed_files"] = 0
            report["metadata"]["version"] = "0.2.0-scout" # Match Rust versioning

        return json.dumps(report, indent=2)


# Legacy alias to maintain API compatibility for anything that might still import it
from yamlr.core.io.sarif_formatter import SarifFormatter as SARIFReporter
