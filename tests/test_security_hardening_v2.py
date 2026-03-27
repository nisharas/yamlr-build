import os
import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from yamlr.core.catalog_manager import CatalogManager
from yamlr.analyzers.security import SecurityAnalyzer
from yamlr.core.engine.crawler import _crawl_with_rust

def test_catalog_manager_real_checksum_v1():
    """Verifies that the real v1 checksum matches the bundled catalog."""
    # Find the bundled catalog path
    from yamlr.core.utils import resolve_bundled_asset
    bundled_v1 = resolve_bundled_asset("catalog/k8s_v1_distilled.json")
    assert bundled_v1 is not None, "Bundled v1 catalog not found"
    
    # We use the parent dir of the bundled catalog as storage_dir for testing
    mgr = CatalogManager(storage_dir=str(bundled_v1.parent))
    
    # Verify the bundled file against the real hash I just implemented
    # Note: verify_catalog internally calls get_catalog_path which looks for k8s_v1_distilled.json
    assert mgr.verify_catalog("v1") is True, "Bundled v1 catalog failed real checksum verification"

def test_security_analyzer_dynamic_tempdir():
    """Verifies that SecurityAnalyzer uses the system temp directory."""
    analyzer = SecurityAnalyzer()
    
    # Get system temp dir
    sys_temp = tempfile.gettempdir()
    
    # Manifest using a path in the system temp directory
    temp_file_path = os.path.join(sys_temp, "test-manifest.yaml")
    
    manifest = {
        "kind": "Pod",
        "metadata": {"name": "test-pod"},
        "spec": {
            "securityContext": {"runAsNonRoot": True},
            "volumes": [
                {
                    "name": "temp-vol",
                    "hostPath": {"path": sys_temp}
                }
            ]
        }
    }
    
    pod_spec = manifest["spec"]
    
    # Should not produce results because sys_temp is now in the default allowed list
    results = analyzer.analyze([manifest])
    
    # If the logic is correct, sys_temp is whitelisted
    assert len(results) == 0, f"System temp path {sys_temp} should be whitelisted"
    
    # Verify that a truly unsafe path is still caught
    unsafe_manifest = {
        "kind": "Pod",
        "metadata": {"name": "unsafe-pod"},
        "spec": {
            "securityContext": {"runAsNonRoot": True},
            "volumes": [
                {
                    "name": "unsafe-vol",
                    "hostPath": {"path": "/etc/shadow"}
                }
            ]
        }
    }
    results = analyzer.analyze([unsafe_manifest])
    assert len(results) == 1
    assert "unsafe hostPath '/etc/shadow'" in results[0].message

def test_crawler_shutil_which_mock():
    """Verifies that the crawler uses shutil.which for discovery."""
    search_root = Path("/tmp/search")
    workspace_root = Path("/tmp/workspace")
    
    # Patch shutil.which where it's used (in crawler.py)
    with patch("yamlr.core.engine.crawler.shutil.which") as mock_which, \
         patch("yamlr.core.engine.crawler.Path.exists") as mock_exists:
        
        # Mock finding the binary in path
        mock_which.return_value = "/usr/local/bin/yamlr-light"
        mock_exists.return_value = False # Force it to use shutil.which for discovery
        
        # We don't want it to actually run the binary, so we'll mock subprocess.run
        with patch("yamlr.core.engine.crawler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout='{"results": []}', returncode=0)
            
            res = _crawl_with_rust(search_root)
            
            # Verify shutil.which was called (at least once for bin_name or str(pb))
            assert mock_which.called
            # Verify it tried to run the "found" binary
            assert mock_run.call_args[0][0][0] == "/usr/local/bin/yamlr-light"
