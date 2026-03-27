"""
Yamlr COMPLIANCE ADAPTERS
-------------------------
Enterprise Orchestration Engine for Custom Compliance Remediation.
Dynamically loads and executes user-provided Python or Shell adapters.

Why: Provides extensibility for organization-specific compliance rules 
     that are not covered by the default Yamlr Safety Engine.
"""

from __future__ import annotations
import json
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("yamlr.pro.compliance.adapters")
__all__ = ['AdapterEngine']

from yamlr.core.engine.adapter_contracts import AdapterContract

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
                contract = self._parse_contract(path)
                self.adapters[rule_id] = {"type": "python", "path": path, "contract": contract}
                logger.debug(f"Loaded Python Adapter for {rule_id} [Contract: {contract}]")
                    
            elif path.suffix in [".sh", ".bat", ".cmd", ".ps1"]:
                contract = self._parse_contract(path)
                self.adapters[rule_id] = {"type": "shell", "path": path, "contract": contract}
                logger.debug(f"Loaded Shell Adapter for {rule_id} [Contract: {contract}]")

    def _parse_contract(self, script_path: Path) -> str:
        """Parses the capability contract from a script header (e.g. # YAMLR_CONTRACT: NO_DELETIONS)."""
        default_contract = "ADD_ONLY"
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                for _ in range(15):
                    line = f.readline()
                    if not line:
                        break
                    if "YAMLR_CONTRACT:" in line:
                        contract_str = line.split("YAMLR_CONTRACT:")[1].strip()
                        if hasattr(AdapterContract, contract_str):
                            return contract_str
                        else:
                            logger.warning(f"Invalid contract '{contract_str}' in {script_path.name}. Defaulting to ADD_ONLY.")
                            return default_contract
        except Exception:
            pass
            
        logger.warning(f"No YAMLR_CONTRACT declared in {script_path.name}. Defaulting to safe-mode: ADD_ONLY.")
        return default_contract

    def get_contract(self, rule_id: str) -> str:
        adapter_info = self.adapters.get(rule_id)
        if not adapter_info:
            normalized_id = rule_id.split("/")[-1]
            adapter_info = self.adapters.get(normalized_id)
        return adapter_info.get("contract", "ADD_ONLY") if adapter_info else "ADD_ONLY"

    def execute_adapter(self, rule_id: str, manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Executes the mapped adapter for the given rule_id, returning the mutated manifest.
        
        Why: Decouples the core engine from external remediation logic, 
             maintaining surgical precision while allowing for custom logic.
        """
        
        # Exact match or normalized match (e.g., rule/missing-namespace -> missing-namespace)
        adapter_info = self.adapters.get(rule_id)
        if not adapter_info:
            normalized_id = rule_id.split("/")[-1]
            adapter_info = self.adapters.get(normalized_id)
            
        if not adapter_info:
            return None
            
        try:
            if adapter_info["type"] == "python":
                # [Hardening] Sandbox: Run Python adapters in a separate process
                # This prevents malicious adapters from accessing Yamlr's internal state.
                script_path = adapter_info["path"]
                cmd = [sys.executable, str(script_path)]
                input_json = json.dumps(manifest).encode("utf-8")
                
                result = subprocess.run(
                    cmd,
                    input=input_json,
                    capture_output=True,
                    check=False,
                    shell=False,
                    timeout=30
                )
                
                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout.decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.error(f"Python Adapter {script_path.name} returned invalid JSON: {e}")
                else:
                    logger.error(f"Python Adapter {script_path.name} failed: {result.stderr.decode('utf-8')}")
                return None
                
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
                    check=False,
                    shell=False,
                    timeout=30
                )
                
                if result.returncode == 0:
                    try:
                        return json.loads(result.stdout.decode("utf-8"))
                    except json.JSONDecodeError as e:
                        logger.error(f"Adapter {script_path.name} returned invalid JSON: {e}")
                else:
                    logger.error(f"Adapter {script_path.name} failed with exit code {result.returncode}:\n{result.stderr.decode('utf-8')}")
                    
        except (subprocess.SubprocessError, OSError, AttributeError) as e:
            logger.error(f"Adapter execution failed for {rule_id}: {e}")
            
        return None
