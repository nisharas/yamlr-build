import json
import pytest
from pathlib import Path
from yamlr.pro.compliance.adapters import AdapterEngine

@pytest.fixture
def temp_adapters_dir(tmp_path):
    # 1. Provide a dummy python adapter
    py_adapter = tmp_path / "MissingNamespace.py"
    py_adapter.write_text(
        "def adapt(manifest):\n"
        "    if 'metadata' not in manifest:\n"
        "        manifest['metadata'] = {}\n"
        "    manifest['metadata']['namespace'] = 'enterprise-default'\n"
        "    return manifest\n"
    )

    # 2. Provide a dummy shell adapter (Python mimicking a shell script returning JSON on stdout)
    # We use a python script called via subprocess to guarantee cross-platform execution in tests
    # instead of strictly relying on bash or bat. We'll label it .bat to trigger the subprocess logic.
    sh_adapter = tmp_path / "UnsafeHostPath.bat"
    # Actually, a bat script is hard to make output pure JSON cross-platform without echo escaping issues.
    # Let's write a standard Python test ensuring the subprocess execution model parses the return string correctly.
    # It will trigger the type="shell" path.
    import sys
    sh_adapter.write_text(
        f"@echo off\n{sys.executable} -c \"import sys, json; m=json.loads(sys.stdin.read()); m['spec']={{'hostPath': 'fixed'}}; print(json.dumps(m))\"\n"
    )
    
    return tmp_path

def test_python_adapter_engine(temp_adapters_dir):
    """Verify that Python modules are dynamically loaded and execute native dict mutation."""
    engine = AdapterEngine(str(temp_adapters_dir))
    assert "MissingNamespace" in engine.adapters
    assert engine.adapters["MissingNamespace"]["type"] == "python"

    manifest = {"kind": "Pod", "metadata": {"name": "test-pod"}}
    
    result = engine.execute_adapter("MissingNamespace", manifest)
    
    assert result is not None
    assert result["metadata"]["namespace"] == "enterprise-default"

def test_shell_adapter_engine(temp_adapters_dir):
    """Verify that external executables receive json string via stdin and return valid JSON on stdout."""
    engine = AdapterEngine(str(temp_adapters_dir))
    assert "UnsafeHostPath" in engine.adapters
    assert engine.adapters["UnsafeHostPath"]["type"] == "shell"

    manifest = {"kind": "Pod", "spec": {"hostPath": "/var/run/docker.sock"}}
    
    result = engine.execute_adapter("UnsafeHostPath", manifest)
    
    assert result is not None
    assert result["spec"]["hostPath"] == "fixed"

def test_adapter_engine_graceful_miss(temp_adapters_dir):
    """Verify engine returns None gracefully if no adapter is found."""
    engine = AdapterEngine(str(temp_adapters_dir))
    
    manifest = {"kind": "Pod"}
    result = engine.execute_adapter("NonExistentRule", manifest)
    
    assert result is None
