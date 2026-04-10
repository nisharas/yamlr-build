"""
HCL PARSER - The Cross-Domain Bridge
-----------------------------------
Extracts resource identities from Terraform (.tf) files.

Why: Enables Yamlr to build a "Full-Stack Safety Graph" by linking
     K8s manifests to the underlying Cloud resources (EBS, RDS, IAM).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import List

from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.parsers.hcl")
__all__ = ["HCLParser", "parse_tf_files"]


class HCLParser:
    """
    Lightweight, high-speed HCL identity extractor.
    Uses regex to extract identities without a full HCL spec parser,
    prioritizing speed and modularity for the initial graph build.
    """

    # Matches: resource "aws_db_instance" "primary" {
    RE_RESOURCE_START = re.compile(r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{')

    # Matches: arn = "arn:aws:rds:..."
    RE_ARN = re.compile(r'arn\s*=\s*"([^"]+)"')

    @classmethod
    def extract_identities(cls, content: str, file_path: str = "") -> List[ManifestIdentity]:
        """
        Extracts identities from HCL content with nesting awareness.
        Why: Prevents false positives from nested blocks or strings.
        """
        identities = []
        lines = content.splitlines()

        stack_depth = 0
        current_identity: Optional[ManifestIdentity] = None

        in_block_comment = False
        for i, line in enumerate(lines):
            # Handle block comments
            if not in_block_comment:
                if "/*" in line:
                    if "*/" in line:
                        # Single line block comment
                        line = re.sub(r"/\*.*?\*/", "", line)
                    else:
                        in_block_comment = True
                        line = line.split("/*")[0]
            else:
                if "*/" in line:
                    in_block_comment = False
                    line = line.split("*/")[-1]
                else:
                    continue

            # [PHASE-14] Strip all comments from the line for processing
            stripped_line = re.sub(r"(?<![:])(#|//).*$", "", line).strip()

            if not stripped_line:
                continue

            # Check for resource start at depth 0
            if stack_depth == 0:
                match = cls.RE_RESOURCE_START.search(stripped_line)
                if match:
                    res_type, res_name = match.groups()
                    current_identity = ManifestIdentity(
                        kind=res_type, name=res_name, namespace="cloud", api_version="terraform/v1", file_path=file_path
                    )
                    # [PHASE-14] Tag as terraform for parallel analysis in processor_helpers
                    current_identity.is_terraform = True

            # Update stack depth
            stack_depth += stripped_line.count("{")
            stack_depth -= stripped_line.count("}")

            # If we are inside a resource block, look for metadata
            if current_identity and stack_depth > 0:
                arn_match = cls.RE_ARN.search(stripped_line)
                if arn_match:
                    if not current_identity.annotations:
                        current_identity.annotations = {}
                    current_identity.annotations["cloud.yamlr.dev/arn"] = arn_match.group(1)

            # If we just exited the resource block, save it
            if current_identity and stack_depth <= 0:
                identities.append(current_identity)
                current_identity = None
                stack_depth = 0  # Guard against negative depth from malformed HCL

        return identities


def parse_tf_files(root_path: Path) -> List[ManifestIdentity]:
    """Scans a directory for .tf files and extracts identities."""
    all_identities = []
    # [Security] Limit crawl depth to prevent DoS on massive repositories (VULN-010)
    MAX_DEPTH = 5

    # We simulate depth limiting as rglob doesn't support it directly in all versions
    for tf_file in root_path.rglob("*.tf"):
        # Check depth relative to root
        try:
            depth = len(tf_file.relative_to(root_path).parts)
            if depth > MAX_DEPTH:
                continue
        except ValueError:
            continue

        try:
            content = tf_file.read_text(encoding="utf-8")
            all_identities.extend(HCLParser.extract_identities(content, str(tf_file)))
        except OSError as e:
            logger.warning(f"Failed to parse Terraform file {tf_file}: {e}")
    return all_identities
