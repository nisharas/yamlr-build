"""
Yamlr REPORTERS
------------------
Structured output generators for CI/CD integration.
"""

import json
import time
from typing import Any, Dict


class JSONReporter:
    """Generates a standard JSON report of the execution."""

    def generate(self, results: Dict[str, Any], duration: float) -> str:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        processed = results.get("processed_files", [])

        # Sanitize results (remove internal keys starting with _)
        sanitized_results = []
        total_issues = 0
        for f in processed:
            # Shallow clone and filter private fields
            data = f.to_dict() if hasattr(f, "to_dict") else (f.__dict__ if hasattr(f, "__dict__") else f)
            clean_f = {k: v for k, v in data.items() if not k.startswith("_")}
            sanitized_results.append(clean_f)
            total_issues += len(data.get("findings", []))

        report = {
            "metadata": {
                "tool": "Yamlr",
                "version": "0.1.0",
                "timestamp": time.time(),
                "duration_seconds": duration,
            },
            "summary": {
                "total_files": len(processed),
                "healed_files": results.get("healed_count", 0),
                "total_issues": total_issues,
            },
            "results": sanitized_results,
        }
        return json.dumps(report, indent=2)


# Legacy alias to maintain API compatibility for anything that might still import it
from yamlr.core.io.sarif_formatter import SarifFormatter as SARIFReporter
