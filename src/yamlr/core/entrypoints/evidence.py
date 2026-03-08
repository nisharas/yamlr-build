import os
import sys
from pathlib import Path

def handle_evidence_command(args, console) -> int:
    """
    Handles the `yamlr evidence <dir>` command for compiling Auditor-Ready reports.
    Requires an Enterprise license.
    """
    from yamlr.core.bridge import YamlrBridge

    # Pro-Gate the command
    if YamlrBridge.get_identity() != "PRO":
        console.print("[bold red]❌ The 'evidence' aggregation command requires Yamlr Enterprise.[/bold red]")
        console.print("Visit [cyan]https://yamlr.dev/pro[/cyan] to upgrade your license.")
        return 1

    evidence_dir = args.dir
    output_format = getattr(args, "format", "pdf")
    output_file = getattr(args, "output_file", None)

    if not os.path.isdir(evidence_dir):
        console.print(f"[bold red]❌ Directory not found:[/bold red] {evidence_dir}")
        return 1

    try:
        from yamlr.pro.compliance.aggregator import EvidenceAggregator
    except ImportError:
         console.print("[bold red]❌ Yamlr Enterprise compliance module missing or corrupted.[/bold red]")
         return 1

    console.print(f"[cyan]🔍 Scanning cryptographic DNA receipts in {evidence_dir}...[/cyan]")
    
    aggregator = EvidenceAggregator(evidence_dir)
    
    # 1. Verification Phase
    is_clean = aggregator.load_and_verify()
    
    receipt_count = len(aggregator.receipts)
    if receipt_count == 0 and not aggregator.tampered_files:
        console.print(f"[yellow]⚠️ No 'evidence-*.json' receipts found in {evidence_dir}[/yellow]")
        return 0

    if not is_clean:
        console.print("\n[bold red]🚨 CRITICAL: CRYPTOGRAPHIC TAMPERING DETECTED 🚨[/bold red]")
        console.print(f"Failed to verify signatures on {len(aggregator.tampered_files)} receipt(s).")
        for f in aggregator.tampered_files:
            console.print(f"  → [red]{f}[/red]")
        console.print("\n[bold yellow]Generating report with TAMPERED watermark...[/bold yellow]")
    else:
        console.print(f"[green]✓ Successfully verified {receipt_count} DNA-signed receipts.[/green]")

    # 2. Compilation Phase
    console.print(f"📊 Compiling Compliance Report ({output_format.upper()})...")

    if not output_file:
        time_suffix = int(os.path.getmtime(evidence_dir) if os.path.exists(evidence_dir) else 0)
        output_file = f"yamlr-audit-report-{time_suffix}.{output_format}"

    try:
        if output_format == "json":
            json_str = aggregator.extract_json()
            Path(output_file).write_text(json_str, encoding="utf-8")
        elif output_format == "pdf":
            aggregator.extract_pdf(output_file)
        else:
            console.print(f"[bold red]❌ Unsupported format:[/bold red] {output_format}")
            return 1
            
        console.print(f"\n[bold green]✅ Auditor-Ready Export Complete![/bold green]")
        console.print(f"📄 Report saved to: [cyan]{output_file}[/cyan]")
        
    except ImportError as e:
        console.print(f"[bold red]❌ Missing Dependency:[/bold red] {e}")
        return 1
    except Exception as e:
        console.print(f"[bold red]❌ Failed to generate report:[/bold red] {e}")
        return 1

    return 0 if is_clean else 1
