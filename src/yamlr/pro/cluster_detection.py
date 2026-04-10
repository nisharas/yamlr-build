#!/usr/bin/env python3
"""
Yamlr Enterprise (Pro) CLUSTER DETECTION
-----------------------------------------
Automates the discovery of the target Kubernetes version by querying
the active cluster context via 'kubectl' or direct API access.

Why: Live version detection ensures that the healing engine is always
     perfectly aligned with the user's infrastructure, enabling
     lossless schema-aware repairs and prophetic migration advice.
"""

import json
import logging
import os
import re
import subprocess
from typing import Optional

logger = logging.getLogger("yamlr.pro.cluster_detection")


class ClusterDetection:
    """
    Auto-discovery engine for live Kubernetes environments.
    """

    _cached_version: Optional[str] = None

    def __init__(self, kubectl_path: str = "kubectl", timeout: float = 0.8):
        self.kubectl_path = kubectl_path
        self.timeout = timeout

    def detect_server_version(self) -> Optional[str]:
        """
        Queries the live environment for the Kubernetes server version.
        Prioritizes cache, then in-cluster environment, then kubectl.

        Returns:
            Standardized version string (e.g., '1.31') or None if detection fails.
        """
        # 1. Return cached result if available
        if ClusterDetection._cached_version:
            return ClusterDetection._cached_version

        # 2. Try In-Cluster Discovery (Cloud Native fallback)
        version = self.detect_from_cluster()

        # 3. Try Local Kubectl Discovery
        if not version:
            version = self.detect_from_kubectl()

        if version:
            ClusterDetection._cached_version = version

        return version

    def detect_from_kubectl(self) -> Optional[str]:
        """Queries the version via 'kubectl version --output=json'."""
        try:
            cmd = [self.kubectl_path, "version", "--client=false", "--output=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, check=False)

            if result.returncode != 0:
                logger.debug(f"ClusterDetection: 'kubectl version' failed (RC={result.returncode}).")
                return None

            data = json.loads(result.stdout)
            version_info = data.get("serverVersion") or data.get("clientVersion")
            if not version_info:
                return None

            git_v = version_info.get("gitVersion", "")
            return self.standardize_version(git_v)

        except subprocess.TimeoutExpired:
            logger.debug(f"ClusterDetection: 'kubectl' timed out after {self.timeout}s.")
        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"ClusterDetection: Error during kubectl discovery: {e}")

        return None

    def detect_from_cluster(self) -> Optional[str]:
        """
        Detects version via KUBERNETES_SERVICE_HOST if running inside a cluster.
        Uses a light urllib check to avoid heavy dependencies like 'kubernetes-python'.
        """
        host = os.environ.get("KUBERNETES_SERVICE_HOST")
        port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")

        if not host:
            return None

        # [PRO-STUB] In-cluster direct API discovery via ServiceAccount token
        # This is a light-touch discovery pattern.
        try:
            import ssl
            import urllib.request

            # Disable SSL verify for light touch (Internal API)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            url = f"https://{host}:{port}/version"
            with urllib.request.urlopen(url, timeout=self.timeout, context=ctx) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    git_v = data.get("gitVersion", "")
                    return self.standardize_version(git_v)
        except Exception as e:
            logger.debug(f"ClusterDetection: In-cluster API discovery failed: {e}")

        return None

    def standardize_version(self, raw_version: str) -> Optional[str]:
        """
        Cleans and standardizes various K8s version formats.
        Format: v1.31.2 -> 1.31, 1.25.0-eks -> 1.25
        """
        match = re.search(r"v?(\d+\.\d+)", raw_version)
        if match:
            return f"v{match.group(1)}"
        return None
