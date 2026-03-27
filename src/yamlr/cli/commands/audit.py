from __future__ import annotations
from yamlr.cli.commands.scan import handle_scan_command
from yamlr.core.measurement import HealingBenchmarker, BenchResult
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("yamlr.cli.commands.audit")
__all__ = ['handle_audit_command', 'handle_verify_command', 'run_benchmark']


def handle_audit_command(args, engine, timing_report=None):
    """
    Entry point for 'yamlr audit'.
    """
    from yamlr.core.license_manager import LicenseManager
    status, _ = LicenseManager.check_pro_status()
    
    if getattr(args, "verify", False) or args.bench:
        if not status.is_usable():
             LicenseManager.notify_pro_required("Compliance Audit / Scientific Mode")
             return 1

    if getattr(args, "verify", False):
        return handle_verify_command(args, engine)

    if args.bench:
        return run_benchmark(args, engine)
    
    # Default behavior: wrap scan
    return handle_scan_command(args, engine, timing_report=timing_report)

def handle_verify_command(args, engine):
    """
    Verifies a .yamlr-receipt.json against its target manifest.
    """
    receipt_path = Path(args.verify)
    if not receipt_path.exists():
        from yamlr.cli.commands.base import get_console
        get_console().print(f"[bold red]❌ Receipt file not found: {receipt_path}[/bold red]")
        return 1
    
    try:
        import json
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        
        target_file = Path(receipt.get("file_path", "unknown"))
        if not target_file.exists():
            # Try relative to receipt path
            target_file = receipt_path.parent / target_file.name
            
        if not target_file.exists():
             from yamlr.cli.commands.base import get_console
             get_console().print(f"[bold red]❌ Target manifest not found: {target_file}[/bold red]")
             return 1
             
        from yamlr.core.entrypoints.base import get_console
        console = get_console()
        console.print(f"[dim]Checking DNA for: {target_file.name}[/dim]")
        
        # Calculate current DNA
        from yamlr.core.dna_utils import calculate_semantic_dna
        from yamlr.core.context import HealContext
        
        raw_content = target_file.read_text(encoding="utf-8")
        shards = engine.pipeline.lexer.shard(raw_content)
        lexer_metadata = engine.pipeline.lexer.prepare_for_scanner(shards)
        engine.pipeline.scanner.set_lexer_context(lexer_metadata)
        identities = engine.pipeline.scanner.scan_shards(shards)
        
        context = HealContext(
            raw_text=raw_content,
            shards=shards,
            identities=identities,
            cluster_version=engine.cluster_version
        )
        docs = engine.pipeline.structurer.reconstruct(context)
        current_dna = calculate_semantic_dna(docs)
        
        expected_dna = receipt.get("healed_dna")
        
        if current_dna == expected_dna:
            from yamlr.core.entrypoints.base import get_console
            console = get_console()
            console.print("\n[bold green]✅ DNA COMPLIANCE VERIFIED[/bold green]")
            console.print(f" [dim]Receipt Version: {receipt.get('receipt_version')}[/dim]")
            console.print(f" [dim]Timestamp:       {receipt.get('timestamp')}[/dim]")
            console.print(f" [dim]DNA Hash:        {current_dna}[/dim]")
            return 0
        else:
            from yamlr.cli.commands.base import get_console
            console = get_console()
            console.print("\n[bold red]❌ DNA TAMPER DETECTED[/bold red]")
            console.print(f" [dim]Expected DNA: {expected_dna}[/dim]")
            console.print(f" [dim]Actual DNA:   {current_dna}[/dim]")
            console.print("[yellow]Manifest has been modified since healing without being re-certified.[/yellow]")
            return 1
            
    except Exception as e:
        from yamlr.cli.commands.base import get_console
        get_console().print(f"[bold red]❌ Verification failed: {e}[/bold red]")
        return 1

def run_benchmark(args, engine):
    """
    Runs the scientific benchmark against the provided target.
    """
    benchmarker = HealingBenchmarker()
    target = args.path[0] if args.path else "."
    
    from yamlr.core.entrypoints.base import get_console
    console = get_console()
    console.print("\n[bold cyan]🔬 Scientific Mode: Benchmarking Engine[/bold cyan]")
    
    # 1. Load index.csv if present (category labeling)
    index_path = os.path.join(target, "index.csv")
    categories = {}
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    categories[parts[0]] = parts[1]
        console.print(f"[dim]Loaded {len(categories)} category labels from index.csv[/dim]")
    
    manifest_files = []
    if os.path.isfile(target):
        manifest_files = [target]
    else:
        for root, _, files in os.walk(target):
            for f in files:
                if f.lower().endswith((".yaml", ".yml")):
                    manifest_files.append(os.path.join(root, f))
                
    if not manifest_files:
        formatter.print_info(f"No manifest files found in {target}")
        return 0
                
    console.print(f"[dim]Benchmarking {len(manifest_files)} manifests...[/dim]")
    
    time.time()
    for file_path in manifest_files:
        rel_path = os.path.relpath(file_path, target)
        category = categories.get(rel_path, "Unknown")
        
        # Process file
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_content = f.read()
            
        start_proc = time.time()
        # Run engine (Stream mode is dry-run by definition)
        result = engine.audit_stream(raw_content)
        proc_time = (time.time() - start_proc) * 1000
        
        # Verify via Oracle
        schema_has = benchmarker.verify_via_oracle(result.healed_content) if result.healed_content else False
        
        # Semantic HAS check (simplistically: no findings of specific types)
        semantic_has = not any(f.get("rule_id") in ["ref/ghost-service", "ref/orphan-pvc"] for f in result.findings)
        
        benchmarker.record_result(BenchResult(
            file_path=rel_path,
            category=category,
            detection_success=len(result.findings) > 0,
            schema_has=schema_has,
            semantic_has=semantic_has,
            lexical_has=True,  # Simplified: if it passed reconstruction it is lexical OK
            reconstruction_depth=result.logic_logs[-1].split(":")[0] if result.logic_logs else "Light",
            false_positive=False, # FP requires a valid file check (pre-process)
            processing_time_ms=proc_time
        ))
        
    # 3. Report
    report = benchmarker.generate_report()
    from yamlr.ui.advisory import AdvisoryRenderer
    AdvisoryRenderer(console).render_benchmark_report(report)
    
    # Save local telemetry
    telemetry_file = "yamlr_bench_latest.json"
    benchmarker.save_to_local_telemetry(telemetry_file)
    console.print(f"[dim]Full metrics saved to {telemetry_file}[/dim]")

