"""Cryptographic manifest signing and signature verification."""
import logging
import os
import re
import sys

from yamlr.ui.theme import console

logger = logging.getLogger(__name__)

def canonicalize_manifest_for_signing(content: str) -> str:
    """Strips signature annotation and normalizes manifest content for deterministic cryptographic hashing."""
    import yaml
    try:
        docs = list(yaml.safe_load_all(content))
        cleaned_docs = []
        for doc in docs:
            if isinstance(doc, dict):
                metadata = doc.get("metadata")
                if isinstance(metadata, dict):
                    annotations = metadata.get("annotations")
                    if isinstance(annotations, dict):
                        annotations.pop("yamlr.dev/signature", None)
                        if not annotations:
                            metadata.pop("annotations", None)
            cleaned_docs.append(doc)
        return yaml.safe_dump_all(cleaned_docs, sort_keys=True)
    except Exception:
        return re.sub(r'^[ \t]*yamlr\.dev/signature:[^\r\n]*\r?\n?', '', content, flags=re.MULTILINE)

def cmd_sign(args):
    import yamlr_native

    from yamlr.core_logic import LicenseManager
    lm = LicenseManager()
    if not lm.check_pro():
        console.print("[bold red][!] Access Denied:[/bold red] Manifest signing is a Pro-tier feature.")
        return

    private_key = os.getenv("YAMLR_PRIVATE_KEY")
    if not private_key:
        console.print("[bold red][!] Error:[/bold red] YAMLR_PRIVATE_KEY environment variable not set.")
        return

    with open(args.path, 'r', encoding="utf-8") as f:
        content = f.read()
    
    canonical_payload = canonicalize_manifest_for_signing(content)
    signature = yamlr_native.native_sign_manifest(canonical_payload, private_key)
    
    # Apply cryptographic signature via atomic AST healer
    success = yamlr_native.native_apply_fix_atomic(
        args.path, 
        "metadata.annotations['yamlr.dev/signature']", 
        signature,
        None, None
    )
    
    if success:
        console.print("[bold green][OK] Manifest signed successfully with Atomic Engine.[/bold green]")
    else:
        # Fallback to structured formatting if atomic healer encounters non-standard blocks
        if "annotations:" in content:
            new_content = re.sub(r'(annotations:\s*)', r'\1yamlr.dev/signature: ' + signature + '\n    ', content, count=1)
        elif "metadata:" in content:
            new_content = re.sub(r'(metadata:\s*)', r'\1annotations:\n    yamlr.dev/signature: ' + signature + '\n  ', content, count=1)
        else:
            new_content = content + f"\nmetadata:\n  annotations:\n    yamlr.dev/signature: {signature}\n"
        with open(args.path, 'w', encoding="utf-8") as f:
            f.write(new_content)
        console.print("[bold green][OK] Manifest signed successfully (Structured Fallback).[/bold green]")

def cmd_verify(args):
    import re
    import sys
    import yamlr_native
    from yamlr.core_logic import LicenseManager
    
    lm = LicenseManager()
    path = getattr(args, "path", ".")
    if not os.path.exists(path):
        console.print(f"[bold red][!] Error: Path '{path}' does not exist.[/bold red]")
        sys.exit(1)
        
    if os.path.isdir(path):
        files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(('.yaml', '.yml'))]
    else:
        files = [path]
        
    if not files:
        console.print(f"[bold yellow][!] No YAML manifests found to verify in '{path}'.[/bold yellow]")
        return
        
    pubkey = lm._get_pubkey()
    if not pubkey:
        console.print("[bold red][!] Error: Public key not found for verification.[/bold red]")
        sys.exit(1)
        
    failed_count = 0
    verified_count = 0
    
    for fpath in files:
        try:
            with open(fpath, 'r', encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            console.print(f"[bold red][!] Error reading {fpath}: {e}[/bold red]")
            failed_count += 1
            continue
            
        sig_match = re.search(r'yamlr\.dev/signature:\s*([A-Za-z0-9_\-\.]+)', content)
        if not sig_match:
            console.print(f"[bold yellow][!] No signature annotation found in {fpath}[/bold yellow]")
            continue
            
        signature = sig_match.group(1).strip()
        canonical_payload = canonicalize_manifest_for_signing(content)
        if yamlr_native.native_verify_manifest(canonical_payload, signature, pubkey):
            console.print(f"[bold green][OK] Signature verified: {fpath}[/bold green]")
            verified_count += 1
        else:
            console.print(f"[bold red][!] Signature verification failed: {fpath}[/bold red]")
            failed_count += 1
            
    if failed_count > 0:
        sys.exit(1)

