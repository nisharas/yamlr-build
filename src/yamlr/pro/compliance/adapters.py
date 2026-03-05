import json
import logging
import importlib.util
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("yamlr.pro.compliance.adapters")

class AdapterEngine:
    """
    Enterprise Orchestration Engine for Custom Compliance Remediation.
    Dynamically loads and executes user-provided Python or Shell adapters.
    """

    def __init__(self, adapters_dir: str):
        self.adapters_dir = Path(adapters_dir)
        self.adapters: Dict[str, Dict[str, Any]] = {}
        if self.adapters_dir.exists() and self.adapters_dir.is_dir():
            self._discover_adapters()

    def _discover_adapters(self):
        """Scans the adapters directory for valid scripts and maps them to rule IDs."""
        for path in self.adapters_dir.iterdir():
            if not path.is_file():
                continue
                
            # Expecting naming convention: rule_id.py or rule-id.sh
            # E.g., MissingNamespace.py
            rule_id = path.stem
            
            if path.suffix == ".py":
                try:
                    spec = importlib.util.spec_from_file_location(rule_id, path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, "adapt") and callable(module.adapt):
                        self.adapters[rule_id] = {"type": "python", "module": module}
                        logger.debug(f"Loaded Python Adapter for {rule_id}")
                    else:
                        logger.warning(f"Python Adapter {path.name} missing 'adapt(manifest: dict)' function.")
                except Exception as e:
                    logger.error(f"Failed to load Python Adapter {path.name}: {e}")
                    
            elif path.suffix in [".sh", ".bat", ".cmd", ".ps1"]:
                self.adapters[rule_id] = {"type": "shell", "path": path}
                logger.debug(f"Loaded Shell Adapter for {rule_id}")

    def execute_adapter(self, rule_id: str, manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Executes the mapped adapter for the given rule_id, returning the mutated manifest."""
        
        # Exact match or normalized match (e.g., rule/missing-namespace -> missing-namespace)
        adapter_info = self.adapters.get(rule_id)
        if not adapter_info:
            normalized_id = rule_id.split("/")[-1]
            adapter_info = self.adapters.get(normalized_id)
            
        if not adapter_info:
            return None
            
        try:
            if adapter_info["type"] == "python":
                return adapter_info["module"].adapt(manifest)
                
            elif adapter_info["type"] == "shell":
                script_path = adapter_info["path"]
                cmd = []
                
                if script_path.suffix == ".sh":
                    cmd = ["bash", str(script_path)]
                elif script_path.suffix == ".ps1":
                    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
                else:
                    cmd = [str(script_path)]
                    
                input_json = json.dumps(manifest).encode("utf-8")
                
                result = subprocess.run(
                    cmd, 
                    input=input_json, 
                    capture_output=True, 
                    check=False
                )
                
                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout.decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.error(f"Adapter {script_path.name} returned invalid JSON: {e}")
                else:
                    logger.error(f"Adapter {script_path.name} failed with exit code {result.returncode}:\n{result.stderr.decode('utf-8')}")
                    
        except Exception as e:
            logger.error(f"Adapter execution failed for {rule_id}: {e}")
            
        return None
