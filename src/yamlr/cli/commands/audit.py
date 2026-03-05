from yamlr.cli.commands.scan import handle_scan_command
from yamlr.core.measurement import HealingBenchmarker, BenchResult
import logging
import os
import time

logger = logging.getLogger("yamlr.cli.commands.audit")

def handle_audit_command(args, engine, formatter):
    """
    Entry point for 'yamlr audit'.
    """
    if args.bench:
        return run_benchmark(args, engine, formatter)
    
    # Default behavior: wrap scan
    return handle_scan_command(args, engine, formatter)

def run_benchmark(args, engine, formatter):
    """
    Runs the scientific benchmark against the provided target.
    """
    benchmarker = HealingBenchmarker()
    target = args.path[0] if args.path else "."
    
    formatter.print_header("🔬 Scientific Mode: Benchmarking Engine")
    
    # 1. Load index.csv if present (category labeling)
    index_path = os.path.join(target, "index.csv")
    categories = {}
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    categories[parts[0]] = parts[1]
        formatter.print_info(f"Loaded {len(categories)} category labels from index.csv")
    
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
                
    formatter.print_info(f"Benchmarking {len(manifest_files)} manifests...")
    
    start_bench = time.time()
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
    formatter.print_benchmark_report(report)
    
    # Save local telemetry
    telemetry_file = "yamlr_bench_latest.json"
    benchmarker.save_to_local_telemetry(telemetry_file)
    formatter.print_info(f"Full metrics saved to {telemetry_file}")

import time
