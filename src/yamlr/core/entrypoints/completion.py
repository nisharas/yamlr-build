import argparse
import sys
import os
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


def generate_powershell() -> str:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return """
# Yamlr PowerShell Completion (Hybrid)
# -----------------------------------
$Script:YamlrCoreLogic = {
    param($wordToComplete, $sourceType)
    
    # Fix: If PowerShell passes the whole line (e.g. 'yamlr s'), strip the command
    $cleanWord = $wordToComplete
    if ($wordToComplete -like "yamlr*") {
        $cleanWord = $wordToComplete -replace "^yamlr\\s*", ""
    }
    
    $staticList = @("scan", "heal", "restore", "explain", "rules", "init", "status", "welcome", "completion", "catalog", "version", "auth", "check", "diagnose", "upgrade", "secure",
                    "--help", "--version", "--kube-version", "--k8s-version", "--catalog", "--verbose", "--summary-only", "-h", "-v", "-s", "--to")
    
    $matches = $staticList | Where-Object { $_ -like "$cleanWord*" }
    
    if ($matches) {
        return $matches | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
    }

    # Dynamic Fallback
    $YamlrExe = "yamlr" # Rely on PATH
    if (Get-Command $YamlrExe -ErrorAction SilentlyContinue) {
        try {
            $suggestions = & $YamlrExe completion --word="$cleanWord"
            if ($suggestions) {
                return $suggestions | ForEach-Object {
                    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
                }
            }
        } catch { }
    }
    return $null
}

# 1. Function Wrapper (Ensures priority and PATH stability)
function yamlr { 
    $bin = Get-Command "yamlr.exe" -ErrorAction SilentlyContinue
    if ($bin) { & $bin.Definition @args } else { yamlr.exe @args }
}

# 2. Unified Completer Block
$Script:YamlrUnifiedCompleter = {
    param($p1, $p2, $p3, $p4, $p5)
    $word = if ($null -ne $p5) { $p3 } else { $p2 }
    if ($null -eq $word) { $word = "" }
    & $Script:YamlrCoreLogic -wordToComplete $word -sourceType "Unified"
}

# 3. Register
Register-ArgumentCompleter -CommandName "yamlr" -ScriptBlock $Script:YamlrUnifiedCompleter
Register-ArgumentCompleter -Native -CommandName "yamlr" -ScriptBlock $Script:YamlrUnifiedCompleter
Register-ArgumentCompleter -Native -CommandName "yamlr.exe" -ScriptBlock $Script:YamlrUnifiedCompleter
"""


def generate_bash() -> str:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return """
# Yamlr Bash Completion
# ---------------------
_yamlr_completions() {
    local cur
    cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=( $(yamlr completion --word="${cur}") )
}
complete -F _yamlr_completions yamlr
complete -F _yamlr_completions Yamlr
"""


def generate_fish() -> str:
    """
    Why: Internal documentation policy compliance.
    What: Auto-generated summary.
    """
    return """
# Yamlr Fish Completion
# ---------------------
complete -c yamlr -f -a "(yamlr completion --word=(commandline -t))"
complete -c Yamlr -f -a "(yamlr completion --word=(commandline -t))"
"""


class ShellInstaller:
    """Handles safe installation of completion scripts into user profiles."""
    
    def __init__(self, console):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.console = console

    def detect_shell(self) -> str:
        """Best-effort shell detection."""
        # Check parent process logic or env vars
        # This is tricky in Python, checking SHELL env is reasonable fallback
        shell_path = os.environ.get("SHELL", "").lower()
        if "bash" in shell_path: return "bash"
        if "zsh" in shell_path: return "zsh"
        if "fish" in shell_path: return "fish"
        
        # Windows check
        if sys.platform == "win32":
            # Assume PowerShell if on Windows primarily, unless in Git Bash (which sets SHELL)
            return "powershell"
            
    def generate_script(self, shell: str) -> str:
        """Generates the completion script for the target shell."""
        if shell == "bash": return generate_bash()
        if shell == "zsh": return generate_zsh()
        if shell == "fish": return generate_fish()
        if shell == "powershell": return generate_powershell()
        return ""

    def get_profile_path(self, shell: str) -> Optional[Path]:
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        home = Path.home()
        if shell == "bash":
            return home / ".bashrc"
        elif shell == "zsh":
            return home / ".zshrc"
        elif shell == "fish":
            return home / ".config" / "fish" / "completions" / "yamlr.fish"
        elif shell == "powershell":
            # Best way: Query the shell itself
            import subprocess
            for exe in ["pwsh", "powershell"]:
                try:
                    res = subprocess.run([exe, "-NoProfile", "-Command", "Write-Output $PROFILE"], capture_output=True, text=True, timeout=2)
                    if res.returncode == 0 and res.stdout.strip():
                        # res.stdout might contain other output? Use last line.
                        path_str = res.stdout.strip().splitlines()[-1]
                        return Path(path_str)
                except:
                    continue
            
            # Fallback (legacy logic)
            if sys.platform == "win32":
                 documents = home / "Documents"
                 return documents / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1"
            else:
                 # PowerShell Core on Linux/Mac
                 return home / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"
        return None

    def get_bin_info(self):
        """Checks if yamlr is in persistent PATH and returns current binary info."""
        current_bin = Path(sys.argv[0]).resolve()
        bin_dir = current_bin.parent
        
        # Check if the directory of the current binary is in the environment PATH
        path_segments = [Path(p).resolve() for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        in_path = any(bin_dir == p for p in path_segments)
        
        # If it's not in the path segments, check if it's a standard system-wide tool
        # (Already handled by the segment check, but we can be extra sure)
        if not in_path:
            import shutil
            # On Windows, shutil.which might find it in cwd. We want to know if it's GLOBALLY found.
            # So we check if shutil.which returns something that is NOT in the current dir.
            where = shutil.which("yamlr") or shutil.which("yamlr.exe")
            if where:
                where_path = Path(where).resolve()
                if where_path.parent != Path.cwd() and where_path.parent != bin_dir:
                    in_path = True
        
        return in_path, current_bin

    def install(self, shell: str):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        profile_path = self.get_profile_path(shell)
        if not profile_path:
            self.console.print(f"[red]Could not determine profile path for {shell}[/red]")
            return 1

        self.console.print(f"Target Profile: [bold]{profile_path}[/bold]")
        
        # Ensure parent dirs exist
        if not profile_path.parent.exists():
            try:
                profile_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                 self.console.print(f"[red]Failed to create config directory: {e}[/red]")
                 return 1

        # Backup
        if profile_path.exists():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = profile_path.parent / (profile_path.name + f".{timestamp}.bak")
            try:
                shutil.copy2(profile_path, backup_path)
                self.console.print(f"[yellow]Backup created:[/yellow] {backup_path}")
            except Exception as e:
                self.console.print(f"[dim yellow]Warning: Backup failed ({e}), proceeding anyway...[/dim yellow]")
        
        # Deterministic Block Markers
        marker_start = "# >>> YAMLR START >>>"
        marker_end = "# <<< YAMLR END <<<"
        
        in_path, current_bin = self.get_bin_info()
        bin_dir = current_bin.parent
        
        # Construct the new block
        lines = [marker_start]
        
        # 1. Path Injection (if binary is not global)
        if not in_path:
            self.console.print(f"[cyan]Info: 'yamlr' not found in persistent PATH. Adding {bin_dir} to your profile...[/cyan]")
            if shell == "powershell":
                lines.append(f'$env:PATH += ";{bin_dir}"')
            elif shell in ["bash", "zsh"]:
                lines.append(f'export PATH="$PATH:{bin_dir}"')

        # 2. Universal Hook
        if shell == "bash":
            lines.append('if command -v yamlr >/dev/null 2>&1; then source <(yamlr completion bash); fi')
        elif shell == "zsh":
            lines.append('if command -v yamlr >/dev/null 2>&1; then autoload -U +X bashcompinit && bashcompinit; source <(yamlr completion zsh); fi')
        elif shell == "powershell":
            lines.append('if (Get-Command yamlr -ErrorAction SilentlyContinue) { yamlr completion powershell | Out-String | Invoke-Expression }')
        
        lines.append(marker_end)
        new_block = "\n" + "\n".join(lines) + "\n"
        
        try:
            content = ""
            if profile_path.exists():
                content = profile_path.read_text(encoding="utf-8", errors="ignore")
            
            # Deterministic Replacement logic
            import re
            pattern = rf"{re.escape(marker_start)}.*?{re.escape(marker_end)}"
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, new_block.strip() + "\n", content, flags=re.DOTALL)
                self.console.print(f"[yellow]Updated existing Yamlr configuration in {shell} profile.[/yellow]")
            else:
                # Add to bottom, ensure newline
                content = content.strip() + "\n" + new_block
            
            profile_path.write_text(content.strip() + "\n", encoding="utf-8")
            self.console.print(f"[bold green]✔ Successfully installed completion for {shell}![/bold green]")
            self.console.print("[dim]Restart your shell to apply changes.[/dim]")
            
        except Exception as e:
            self.console.print(f"[red]Installation failed: {e}[/red]")
            return 1
            
        return 0

    def generate_suggestions(self, word: str):
        """Standard suggestion logic for the fast-path."""
        # Simple command set for fast response. 
        # For full flag completion, we'd need the full parser, 
        # but the first word is usually a subcommand.
        commands = ["scan", "heal", "restore", "explain", "rules", "init", "status", "welcome", "completion", "catalog", "version", "auth", "check", "diagnose", "upgrade", "secure"]
        
        if word.startswith("-"):
            # Global flags
            flags = ["--help", "--version", "--kube-version", "--k8s-version", "--catalog", "--verbose", "--summary-only", "-h", "-v", "-s"]
            for f in flags:
                if f.startswith(word):
                    print(f)
        else:
            for cmd in commands:
                if cmd.startswith(word):
                    print(cmd)


def get_runtime_suggestions(parser: argparse.ArgumentParser, word: str) -> List[str]:
    """
    Returns a list of suggestions based on the word being typed.
    """
    matches = []
    is_flag = word.startswith("-")
    
    # 1. Subcommands
    if not is_flag:
        if parser._subparsers:
            for action in parser._subparsers._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for cmd in action.choices.keys():
                        if cmd.startswith(word):
                            matches.append(cmd)
    
    # 2. Flags
    # If the user started a flag or we found no subcommands, suggest all flags
    if is_flag or not matches:
        all_flags = set()
        for action in parser._actions:
            all_flags.update(action.option_strings)
        
        if parser._subparsers:
            for action in parser._subparsers._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for sub in action.choices.values():
                        for sub_act in sub._actions:
                            all_flags.update(sub_act.option_strings)
        
        for f in all_flags:
            if f.startswith(word):
                matches.append(f)
            
    return sorted(list(set(matches)))


def handle_completion_command(args, parser: argparse.ArgumentParser, console):
    """
    Outputs the shell completion script dynamically generated from the current parser.
    """
    # 1. Runtime Callback Handling
    if getattr(args, "word", None) is not None:
        suggestions = get_runtime_suggestions(parser, args.word)
        for s in suggestions:
            print(s)
        return 0

    # Auto-Install Logic
    if getattr(args, "install", False):
        installer = ShellInstaller(console)
        shell = args.shell or installer.detect_shell()
        
        # Fish specific handling for install (overwrite file instead of append)
        if shell == "fish":
            path = installer.get_profile_path("fish")
            if not path: return 1
            
            console.print(f"Target: [bold]{path}[/bold]")
            if path.exists():
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = path.with_suffix(f".{timestamp}.bak")
                shutil.copy2(path, backup)
                console.print(f"[yellow]Backup created:[/yellow] {backup}")
            
            # Ensure dir
            path.parent.mkdir(parents=True, exist_ok=True)
            
            content = generate_fish()
            path.write_text(content, encoding="utf-8")
            
            console.print(f"[bold green]✔ Successfully installed completion for Fish![/bold green]")
            return 0
            
        return installer.install(shell)

    shell = args.shell
    if shell:
        shell = shell.lower()

    if not shell:
        console.print("[bold]Autocompletion Generator[/bold]")
        console.print("Please specify a shell to generate the script for:\n")
        console.print("  [cyan]yamlr completion powershell[/cyan]")
        console.print("  [cyan]yamlr completion bash[/cyan]")
        console.print("  [cyan]yamlr completion zsh[/cyan]")
        console.print("  [cyan]yamlr completion fish[/cyan]")
        console.print("\n[bold green]--install[/bold green] : Automatically install to your shell profile")
        return 1

    if shell == "powershell":
        print(generate_powershell().strip())
    elif shell == "bash":
        print(generate_bash().strip())
    elif shell == "zsh":
        # Reuse bash with preamble
        bash_script = generate_bash().strip()
        print(f"autoload -U +X bashcompinit && bashcompinit\n{bash_script}")
    elif shell == "fish":
        print(generate_fish().strip())
    else:
        console.print(f"[red]Unsupported shell: {shell}[/red]")
        return 1

    return 0
