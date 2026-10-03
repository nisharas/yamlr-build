import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from yamlr.ui.theme import ICON_ALERT, ICON_SUCCESS, console


class BackupManager:
    """Manages atomic file checkpoints and rollbacks during automated healing."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).absolute()
        self.backup_dir = self.workspace_root / ".yamlr" / "backups"
        self.index_path = self.backup_dir / "index.json"
        self._ensure_infra()

    def _ensure_infra(self):
        """Initializes the hidden backup infrastructure."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            with open(self.index_path, "w") as f:
                json.dump({"sessions": []}, f)

    def create_checkpoint(self, files_to_backup: List[str]) -> str:
        """Clones manifests into a session-based checkpoint before mutation."""
        session_id = f"session_{int(time.time())}"
        session_dir = self.backup_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        manifest = []
        for f_path in files_to_backup:
            src = Path(f_path).absolute()
            if not src.exists():
                continue
                
            # Relative path within session to mirror workspace
            rel_path = src.relative_to(self.workspace_root)
            dst = session_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(src, dst)
            manifest.append({
                "original_path": str(src),
                "backup_rel_path": str(rel_path)
            })
            
        # Update Index
        with open(self.index_path, "r+") as f:
            data = json.load(f)
            data["sessions"].append({
                "id": session_id,
                "timestamp": time.ctime(),
                "files": manifest
            })
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            
        self._cleanup_old_backups()
        return session_id

    def _cleanup_old_backups(self):
        """Maintains backup hygiene by keeping only the last 10 sessions."""
        try:
            with open(self.index_path, "r") as f:
                data = json.load(f)
            
            if len(data["sessions"]) > 10:
                # Identify sessions to remove
                to_remove = data["sessions"][:-10]
                data["sessions"] = data["sessions"][-10:]
                
                for session in to_remove:
                    session_path = self.backup_dir / session["id"]
                    if session_path.exists():
                        shutil.rmtree(session_path)
                
                with open(self.index_path, "w") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass

    def restore_last_session(self) -> bool:
        """Performs a 'Reverse Patch' to restore the most recent checkpoint."""
        with open(self.index_path, "r") as f:
            data = json.load(f)
            
        if not data["sessions"]:
            console.print("\n[bold red][!] RESTORE FAILED:[/bold red] No backup checkpoints found in this workspace.")
            return False
            
        last_session = data["sessions"][-1]
        session_dir = self.backup_dir / last_session["id"]
        
        console.print(f"\n[bold cyan][!] Restoring Checkpoint:[/bold cyan] {last_session['id']} ({last_session['timestamp']})")
        
        success_count = 0
        for entry in last_session["files"]:
            src = session_dir / entry["backup_rel_path"]
            dst = Path(entry["original_path"])
            
            try:
                shutil.copy2(src, dst)
                console.print(f"    {ICON_SUCCESS} Restored: [dim]{dst.name}[/dim]")
                success_count += 1
            except Exception as e:
                console.print(f"    [bold red][X] Failed:[/bold red] {dst.name} ({e})")
                
        if success_count > 0:
            console.print(f"\n[bold green]{ICON_SUCCESS} Atomic Restore Complete ({success_count} files).[/bold green]")
            # Remove the session from index after successful restore
            data["sessions"].pop()
            with open(self.index_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        return False
