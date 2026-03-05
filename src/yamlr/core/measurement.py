#!/usr/bin/env python3
"""
Yamlr MEASUREMENT MODULE
------------------------
Implements the 'Scientific Mode' benchmarking engine.
Allows Yamlr to measure its own performance against a labeled corpus.

Key Metrics:
- Schema HAS: Passes kubectl --validate=strict
- Semantic HAS: No ghost resources / referential orphans
- Lexical HAS: Perfect YAML syntax and normalization

Author: Nishar A Sunkesala / Yamlr Team
Date: 2026-02-21
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger("yamlr.core.measurement")

@dataclass
class BenchResult:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    file_path: str
    category: str
    detection_success: bool
    schema_has: bool
    semantic_has: bool
    lexical_has: bool
    false_positive: bool
    reconstruction_depth: str = "N/A" # Light, Medium, Heavy
    processing_time_ms: float = 0.0

@dataclass
class CategoryStats:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    name: str
    total_files: int = 0
    detected: int = 0
    healed: int = 0 # Passed all HAS dims
    false_positives: int = 0
    avg_depth: Dict[str, int] = field(default_factory=lambda: {"Light": 0, "Medium": 0, "Heavy": 0})
    
    @property
    def has_score(self) -> float:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        if self.total_files == 0: return 0.0
        return (self.healed / self.total_files) * 100.0

class HealingBenchmarker:
    """
    Orchestrates the scientific audit of a manifest corpus.
    """
    def __init__(self):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.results: List[BenchResult] = []
        self.kubectl_path = "kubectl"
        self._offline_mode = None # Cache for connectivity
        self.category_map: Dict[str, CategoryStats] = {}
        
    def _check_connectivity(self) -> bool:
        """Checks if kubectl can reach a cluster (with cache)."""
        if self._offline_mode is not None:
            return not self._offline_mode
            
        try:
            import subprocess
            # Quick check with short timeout
            proc = subprocess.run(
                [self.kubectl_path, "version", "--request-timeout=1s"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )
            self._offline_mode = proc.returncode != 0
        except Exception:
            self._offline_mode = True
            
        return not self._offline_mode

    def verify_via_oracle(self, yaml_content: str) -> bool:
        """
        Validates content using kubectl (if available) or internal fallback.
        """
        if not yaml_content:
            return False

        # 1. Use internal validator if offline
        if not self._check_connectivity():
            from yamlr.validators.schema_validator import SchemaValidator
            validator = SchemaValidator()
            import yaml
            try:
                data = yaml.safe_load(yaml_content)
                # If it's a list (multi-doc), validate each
                if isinstance(data, list):
                    for doc in data:
                        # If any document fails validation, the whole content fails
                        if validator.validate_full_document(doc): return False
                    return True # All documents passed
                errors = validator.validate_full_document(data)
                return len(errors) == 0
            except:
                return False

        # 2. Online validation via kubectl
        cmd = [self.kubectl_path, "apply", "--dry-run=server", "--validate=strict", "-f", "-"]
        try:
            import subprocess
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = proc.communicate(input=yaml_content)
            return proc.returncode == 0
        except Exception:
            return False

    def record_result(self, result: BenchResult):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.results.append(result)
        
        stats = self.category_map.setdefault(result.category, CategoryStats(name=result.category))
        stats.total_files += 1
        if result.detection_success: stats.detected += 1
        if result.schema_has and result.semantic_has and result.lexical_has:
            stats.healed += 1
        if result.false_positive: stats.false_positives += 1
        
        if result.reconstruction_depth in stats.avg_depth:
            stats.avg_depth[result.reconstruction_depth] += 1

    def generate_report(self) -> Dict[str, Any]:
        """
        Generates the final multi-dimensional assessment.
        """
        total = len(self.results)
        if total == 0:
            return {"error": "No results recorded"}

        overall_healed = sum(1 for r in self.results if r.schema_has and r.semantic_has and r.lexical_has)
        
        # Sort categories by weakest HAS for the 'Top 10 Weakest' report
        sorted_categories = sorted(
            self.category_map.values(), 
            key=lambda x: x.has_score
        )

        return {
            "overall_has": (overall_healed / total) * 100.0,
            "total_files": total,
            "category_breakdown": {
                c.name: {
                    "has": c.has_score,
                    "detection_rate": (c.detected / c.total_files * 100) if c.total_files > 0 else 0,
                    "fp_rate": (c.false_positives / c.total_files * 100) if c.total_files > 0 else 0,
                    "depth_distribution": c.avg_depth
                } for c in sorted_categories
            },
            "top_10_weakest": [c.name for c in sorted_categories[:10]]
        }

    def save_to_local_telemetry(self, output_path: str):
        """
        Strictly local NDJSON storage.
        """
        with open(output_path, "w") as f:
            for r in self.results:
                f.write(json.dumps(asdict(r)) + "\n")
        logger.info(f"Local telemetry saved to {output_path}")
