import sys
import os
from pathlib import Path

# Add src to sys.path
ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

def render_help():
    from rich.console import Console
    from yamlr.cli.help_formatter import print_kubectl_help
    
    output_path = SRC_DIR / "yamlr" / "cli" / "help" / "help_main.ansi"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use a high-width console to avoid wrapping issues in pre-render
    # [Engine Standard] 100 columns is safe for most terminals
    console = Console(width=100, force_terminal=True, color_system="truecolor")
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Redirect rich output to the file using a capture context
        with console.capture() as capture:
            print_kubectl_help(console, "yamlr", show_all=False)
        f.write(capture.get())
        
    print(f"DONE: Pre-rendered help saved to {output_path}")

    # Also render the --all version
    all_output_path = SRC_DIR / "yamlr" / "cli" / "help" / "help_all.ansi"
    with open(all_output_path, "w", encoding="utf-8") as f:
        with console.capture() as capture:
            print_kubectl_help(console, "yamlr", show_all=True)
        f.write(capture.get())
        
    print(f"DONE: Pre-rendered --all help saved to {all_output_path}")

if __name__ == "__main__":
    render_help()
