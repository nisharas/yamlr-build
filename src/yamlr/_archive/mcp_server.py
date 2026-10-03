"""Model Context Protocol (MCP) server for IDE, editor, and automated tooling integrations.

Enables developer tools and editors to inspect, validate, and heal Kubernetes manifests
using the Yamlr analysis engine over standard I/O JSON-RPC.
"""

import json
import os
import sys
from typing import Any, Dict, List


def run_mcp_server():
    """Main loop for the MCP Stdio server."""
    # Note: This is a minimalist implementation of the MCP protocol over stdio.
    # In a full production build, we would use the 'mcp' python SDK.
    
    while True:
        line = sys.stdin.readline()
        if not line:
            break
            
        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})
            req_id = request.get("id")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {
                                "listChanged": False
                            }
                        },
                        "serverInfo": {
                            "name": "yamlr-forensic-engine",
                            "version": "0.1.0"
                        }
                    }
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "scan_manifests",
                                "description": "Audit Kubernetes manifests for schema and integrity violations.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Path to scan."}
                                    }
                                }
                            },
                            {
                                "name": "heal_manifests",
                                "description": "Automatically remediate violations in Kubernetes manifests.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Path to heal."}
                                    }
                                }
                            },
                            {
                                "name": "get_resource_dependencies",
                                "description": "Query the cross-resource graph to find resources bound to a target resource (e.g., ConfigMaps bound to Deployment).",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string", "description": "Path to the manifests to build the graph."},
                                        "kind": {"type": "string", "description": "Target resource kind (e.g., Deployment)."},
                                        "name": {"type": "string", "description": "Target resource name (e.g., api-server)."}
                                    },
                                    "required": ["path", "kind", "name"]
                                }
                            },
                            {
                                "name": "get_openapi_schema",
                                "description": "Retrieve strict OpenAPI schema rules for a specific resource kind.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "kind": {"type": "string", "description": "Resource kind (e.g., Ingress)."},
                                        "k8s_version": {"type": "string", "description": "Kubernetes version (e.g., 1.30)."}
                                    },
                                    "required": ["kind", "k8s_version"]
                                }
                            },
                            {
                                "name": "propose_infrastructure_mutation",
                                "description": "Safely propose an infrastructure mutation (AI Guardrail). Dry-runs the patch through the Yamlr engine to detect structural/health regressions.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {"type": "string", "description": "Target file to mutate."},
                                        "proposed_patch": {"type": "string", "description": "The exact patch string to apply."}
                                    },
                                    "required": ["file_path", "proposed_patch"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                result = _execute_tool(tool_name, tool_args)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": "Method not found"}
                }
                
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            
        except Exception as e:
            err_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_response) + "\n")
            sys.stdout.flush()

def _execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Bridges MCP tool invocations to the underlying analysis and healing engine."""
    import yamlr_native

    from yamlr.cli.main import detect_version, execute_pipeline, initialize_engine
    
    try:
        if name == "get_openapi_schema":
            kind = args.get("kind", "")
            version = args.get("k8s_version", "1.30")
            try:
                if hasattr(yamlr_native, 'native_get_schema_info'):
                    schema_data = yamlr_native.native_get_schema_info(kind, version)
                    return {"status": "success", "schema": schema_data, "k8s_version": version}
                schemas = yamlr_native.native_get_schema_for_version(version)
                matching = [
                    {
                        "api_version": s.api_version,
                        "kind": s.kind,
                        "properties": [
                            {"name": p.name, "type": p.prop_type, "required": p.required}
                            for p in s.properties
                        ]
                    }
                    for s in schemas if not kind or s.kind.lower() == kind.lower()
                ]
                return {"status": "success", "schema": matching, "schemas": matching, "k8s_version": version}
            except Exception as e:
                return {"status": "error", "message": f"Failed to retrieve schema: {e}"}
            
        if name == "propose_infrastructure_mutation":
            file_path = args.get("file_path")
            patch = args.get("proposed_patch")
            if not file_path or not patch:
                return {"status": "error", "message": "Missing file_path or proposed_patch"}

            from yamlr.core.stages.health_scorer import HealthScoringStage
            version = detect_version()
            schemas = initialize_engine(version)

            # 1. Baseline analysis of original file if it exists
            orig_content = ""
            orig_score = 100.0
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        orig_content = f.read()
                    if orig_content.strip():
                        orig_shards = yamlr_native.native_shard(orig_content)
                        orig_v = list(yamlr_native.native_check_schema_violations(orig_content, schemas))
                        orig_iv = list(yamlr_native.native_audit_forensics(orig_shards))
                        orig_score = HealthScoringStage.calculate_score(orig_v + orig_iv)
                except Exception:
                    pass

            # 2. In-memory validation of the proposed mutation
            try:
                mutated_shards = yamlr_native.native_shard(patch)
                if not mutated_shards:
                    return {
                        "status": "success",
                        "mutation_status": "REJECTED",
                        "before_score": orig_score,
                        "after_score": 0.0,
                        "health_delta": f"{-orig_score:+.1f}",
                        "message": "Proposed mutation produced empty or unparseable YAML."
                    }

                mutated_v = list(yamlr_native.native_check_schema_violations(patch, schemas))
                mutated_iv = list(yamlr_native.native_audit_forensics(mutated_shards))
                new_score = HealthScoringStage.calculate_score(mutated_v + mutated_iv)
                delta = new_score - orig_score

                has_critical = any("critical" in str(getattr(v, "severity", "")).lower() or "error" in str(getattr(v, "severity", "")).lower() for v in (mutated_v + mutated_iv))

                if len(mutated_v) == 0 and not has_critical and delta >= 0:
                    mutation_status = "APPROVED"
                    msg = "Mutation preserves structural integrity and meets Kubernetes schema standards."
                elif has_critical or delta < -10.0:
                    mutation_status = "REJECTED"
                    msg = "Mutation introduces critical security, topology, or schema regressions."
                else:
                    mutation_status = "WARNING"
                    msg = "Mutation contains warnings or non-critical best practice violations."

                return {
                    "status": "success",
                    "mutation_status": mutation_status,
                    "before_score": round(orig_score, 1),
                    "after_score": round(new_score, 1),
                    "health_delta": f"{delta:+.1f}",
                    "schema_violations": [{"field": v.field_path, "message": v.message} for v in mutated_v],
                    "integrity_violations": [{"check": v.check_name, "severity": v.severity, "message": v.message} for v in mutated_iv],
                    "message": msg
                }
            except Exception as e:
                return {"status": "error", "message": f"In-memory mutation analysis failed: {e}"}

        path = args.get("path", ".")
        version = detect_version()
        schemas = initialize_engine(version)
        report = execute_pipeline(path, schemas)
        
        if name == "get_resource_dependencies":
            target_kind = args.get("kind")
            target_name = args.get("name")
            dependencies = []
            
            # Simple python-level topology bridge. (Real logic uses the TopologyManager or native Rust graph)
            for res in report.results:
                for ref in getattr(res, "dependencies", []):
                    if ref.get("kind") == target_kind and ref.get("name") == target_name:
                        dependencies.append(f"{res.identity.kind} {res.identity.name}")
            
            return {
                "status": "success",
                "target": f"{target_kind}/{target_name}",
                "dependencies": dependencies
            }

        
        applied_fixes = 0
        if name == "heal_manifests":
            for res in report.results:
                if res.suggested_fixes:
                    for fix in res.suggested_fixes:
                        # Atomic healing through the native core
                        success = yamlr_native.native_apply_fix_atomic(
                            res.file_path, fix.field_path, fix.suggested_value,
                            getattr(res.identity, 'kind', None), getattr(res.identity, 'name', None)
                        )
                        if success: applied_fixes += 1
            
        # Serialize report for agent consumption
        results = []
        for res in report.results:
            violations = []
            for v in getattr(res, "violations", []):
                violations.append({"field": v.field_path, "message": v.message})
            for v in getattr(res, "integrity_violations", []):
                violations.append({"check": v.check_name, "message": v.message})
                
            results.append({
                "file": res.file_path,
                "score": res.health_score,
                "violations": violations
            })
            
        return {
            "status": "success",
            "total_files": report.total_files,
            "applied_fixes": applied_fixes,
            "results": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    run_mcp_server()
