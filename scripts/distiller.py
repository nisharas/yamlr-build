import yamlr_native
import argparse
import sys
import os

def run_distiller():
    """Transforms raw Kubernetes OpenAPI specifications into optimized schema definitions."""
    parser = argparse.ArgumentParser(prog="yamlr-distiller", description="Yamlr Schema Distiller (Standard)")
    parser.add_argument("input", help="Path to raw OpenAPI JSON spec")
    parser.add_argument("--output", help="Output path for distilled schema", default="distilled_schema.json")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
        
    try:
        with open(args.input, 'r') as f:
            raw_json = f.read()
            
        print(f"[!] Distilling schema: {args.input}")
        distilled = yamlr_native.native_distill_schema(raw_json)
        
        with open(args.output, 'w') as f:
            f.write(distilled)
            
        print(f"[OK] Distilled schema saved to: {args.output}")
        
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_distiller()
