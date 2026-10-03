"""Scanning pipeline for manifest discovery, sharding, and analysis."""
import logging
import os
import shutil
from typing import Any, List, Optional

from yamlr.core.stages.health_scorer import HealthScoringStage
from yamlr.core.stages.integrity_auditor import IntegrityAuditStage
from yamlr.core.stages.schema_validator import SchemaValidationStage
from yamlr.core.stages.topology_analyzer import TopologyAnalysisStage
from yamlr.ui.theme import console

logger = logging.getLogger(__name__)

YAML_EXTENSIONS = ('.yaml', '.yml')


def _discover_manifests(path: str) -> List[str]:
    """Internal helper to find YAML manifests in a directory."""
    if os.path.isfile(path):
        return [path]

    found = []
    for root, _, files in os.walk(path):
        for fname in files:
            if fname.endswith(YAML_EXTENSIONS) and not fname.endswith('.yamlr.tmp'):
                found.append(os.path.join(root, fname))
    return found


def _reconstruct_or_fallback(yamlr_native, doc_shards, fallback_content):
    if hasattr(yamlr_native, 'native_reconstruct_yaml'):
        try:
            return yamlr_native.native_reconstruct_yaml(doc_shards)
        except Exception as e:
            logger.warning("native_reconstruct_yaml execution failed: %s; using fallback content", e)
            return fallback_content
    return fallback_content


def _split_and_process_docs(yamlr_native, file_path, shards, schemas, content):
    """Internal helper to split multi-doc YAMLs and yield results."""
    doc_shards = []
    for shard in shards:
        if shard.is_doc_boundary:
            if doc_shards:
                doc_content = _reconstruct_or_fallback(yamlr_native, doc_shards, content)
                result = _process_document_shards(
                    yamlr_native, file_path, doc_shards, schemas, doc_content
                )
                if result is not None:
                    yield result
                doc_shards = []
        else:
            doc_shards.append(shard)

    if doc_shards:
        doc_content = _reconstruct_or_fallback(yamlr_native, doc_shards, content)
        result = _process_document_shards(
            yamlr_native, file_path, doc_shards, schemas, doc_content
        )
        if result is not None:
            yield result



def streaming_scan(path: str, schemas: list):
    """Generator that yields ResourceResult objects for each Kubernetes manifest found."""
    try:
        import yamlr_native
    except ImportError:
        console.print("[bold red][!] Native core not available. Install with: maturin develop[/bold red]")
        return

    for file_path in _discover_manifests(path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            process_content = content
            if "{{" in content:
                from yamlr.core.template_masker import mask_go_templates
                process_content, _ = mask_go_templates(content)

            shards = yamlr_native.native_shard(process_content)
            if not shards:
                continue

            yield from _split_and_process_docs(yamlr_native, file_path, shards, schemas, process_content)

        except (OSError, UnicodeDecodeError) as e:
            logger.debug("Skipping unreadable or invalid file '%s': %s", file_path, e)
            continue


def _calculate_health_score(violations: list) -> float:
    """Calculates manifest health score via HealthScoringStage."""
    return HealthScoringStage.calculate_score(violations)


def _process_document_shards(yamlr_native, file_path, shards, schemas, raw_content):
    """Processes a single YAML document's shards through the forensic pipeline."""
    identity = yamlr_native.extract_native_identity(shards)

    # Run schema validation if schemas are available
    violations = SchemaValidationStage.validate(yamlr_native, raw_content, schemas, identity)

    # Run integrity checks via the forensic audit engine
    integrity_violations = IntegrityAuditStage.audit(yamlr_native, shards)

    # Build suggested fixes from violations
    suggested_fixes = list(violations)

    # Calculate health score deterministically via dedicated stage
    all_violations = list(violations) + list(integrity_violations)
    health_score = HealthScoringStage.calculate_score(all_violations)

    # Extract relationships
    relationships = []
    if identity and hasattr(identity, 'relationships'):
        relationships = identity.relationships

    return yamlr_native.ResourceResult(
        file_path=file_path,
        identity=identity,
        violations=violations,
        integrity_violations=integrity_violations,
        health_score=health_score,
        suggested_fixes=suggested_fixes,
        relationships=relationships,
    )


def audit_topology_outages(results: list) -> list:
    """Cross-resource topology analysis to detect inter-manifest deadlocks."""
    return TopologyAnalysisStage.analyze(results)


def scan_helm_chart(chart_path: str, schemas: list):
    """Renders a Helm chart in-memory and scans the resulting resources."""
    import subprocess
    try:
        import yamlr_native
    except ImportError:
        console.print("[bold red][!] Native core not available. Install with: maturin develop[/bold red]")
        return

    has_helm = shutil.which("helm") is not None
    if has_helm:
        try:
            proc = subprocess.run(
                ["helm", "template", "yamlr-audit", chart_path],
                capture_output=True,
                text=True,
                check=False
            )
            if proc.returncode == 0 and proc.stdout.strip():
                content = proc.stdout
                shards = yamlr_native.native_shard(content)
                if shards:
                    yield from _split_and_process_docs(
                        yamlr_native, f"{chart_path} (helm template)", shards, schemas, content
                    )
                    return
        except Exception as e:
            logger.debug("Helm template subprocess execution failed: %s", e)

    # In-Process Fallback: scan values files, templates/ directory, and charts/ subcharts directly
    values_file = os.path.join(chart_path, "values.yaml")
    if os.path.isfile(values_file):
        yield from streaming_scan(values_file, schemas)

    try:
        for f in os.listdir(chart_path):
            if f.startswith("values-") and (f.endswith(".yaml") or f.endswith(".yml")):
                yield from streaming_scan(os.path.join(chart_path, f), schemas)
    except OSError:
        pass

    templates_dir = os.path.join(chart_path, "templates")
    if os.path.isdir(templates_dir):
        yield from streaming_scan(templates_dir, schemas)

    charts_dir = os.path.join(chart_path, "charts")
    if os.path.isdir(charts_dir):
        try:
            for item in os.listdir(charts_dir):
                subchart_path = os.path.join(charts_dir, item)
                if os.path.isdir(subchart_path):
                    yield from scan_helm_chart(subchart_path, schemas)
        except OSError:
            pass


def scan_kustomize_dir(kustomize_path: str, schemas: list):
    """Renders a Kustomize overlay in-memory and scans the resulting resources."""
    import subprocess
    try:
        import yamlr_native
    except ImportError:
        console.print("[bold red][!] Native core not available. Install with: maturin develop[/bold red]")
        return

    has_kustomize = shutil.which("kustomize") is not None
    has_kubectl = shutil.which("kubectl") is not None

    if has_kustomize or has_kubectl:
        try:
            proc = None
            if has_kustomize:
                proc = subprocess.run(
                    ["kustomize", "build", kustomize_path],
                    capture_output=True,
                    text=True,
                    check=False
                )
            if (proc is None or proc.returncode != 0) and has_kubectl:
                proc = subprocess.run(
                    ["kubectl", "kustomize", kustomize_path],
                    capture_output=True,
                    text=True,
                    check=False
                )

            if proc and proc.returncode == 0 and proc.stdout.strip():
                content = proc.stdout
                shards = yamlr_native.native_shard(content)
                if shards:
                    yield from _split_and_process_docs(
                        yamlr_native, f"{kustomize_path} (kustomize build)", shards, schemas, content
                    )
                    return
        except Exception as e:
            logger.debug("Kustomize subprocess execution error for '%s': %s", kustomize_path, e)

    # In-Process Fallback: scan directory manifests directly without external binary
    yield from streaming_scan(kustomize_path, schemas)

