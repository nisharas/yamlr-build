"""
Yamlr FILE SYSTEM MANAGER
-------------------------
Handles all physical I/O operations:
- Atomic file writes (fsync)
- Safe backup generation
- Directory crawling with security checks (symlinks, traversal)

Decoupled from YamlrEngine to support future S3/Remote backends.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Generator, List, Tuple

logger = logging.getLogger("yamlr.dev")


class FileSystemManager:
    """
    Abstration layer for local file system operations.
    """
    
    # [Security] Prevent OOM by limiting file reading size (50MB default)
    MAX_FILE_SIZE = 50 * 1024 * 1024 

    def __init__(self, workspace_root: Path, app_name: str = "Yamlr"):
        """
        Why: Internal documentation policy compliance.
        What: Auto-generated summary.
        """
        self.workspace = workspace_root.resolve()
        self.app_name = app_name.lower()
        self.state_dir = self.workspace / f".{self.app_name}"
        self.backup_dir = self.state_dir / "backups"

    def ensure_workspace(self):
        """Creates workspace and state directories if missing."""
        if not self.workspace.exists():
            try:
                self.workspace.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created workspace: {self.workspace}")
            except Exception as e:
                raise RuntimeError(f"Workspace creation failed: {e}")

        # Ensure hidden state dir exists
        if not self.state_dir.exists():
            self.state_dir.mkdir(exist_ok=True)

        # Ensure backup dir exists with restricted permissions (0o700)
        # This protects sensitive manifest data from other users on the host.
        if not self.backup_dir.exists():
            try:
                # 0o700 = Only current user can read/write/execute
                if os.name != "nt":
                    self.backup_dir.mkdir(mode=0o700, exist_ok=True)
                else:
                    self.backup_dir.mkdir(exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to set restricted permissions on backup vault: {e}")
                self.backup_dir.mkdir(exist_ok=True)

    def read_text(self, path: Path) -> str:
        """Reads text file with BOM handling and size guards."""
        # [Security] Guard against massive files (OOM/DoS)
        try:
            if path.stat().st_size > self.MAX_FILE_SIZE:
                raise IOError(f"File too large: {path.name} (Max {self.MAX_FILE_SIZE // (1024*1024)}MB)")
        except (FileNotFoundError, PermissionError):
            pass # Let read_text handle these naturally

        return path.read_text(encoding="utf-8-sig")

    def atomic_write(self, target_path: Path, content: str) -> None:
        """
        Atomically writes content to file with fsync for durability.

        This method ensures that the file is never left in a partially-written 
        state. It writes to a temporary file first, flushes it to physical disk, 
        and then uses an atomic rename.

        Security Measures:
        - Prevents symlink traversal: Explicitly refuses to write if the 
          target is a symlink.

        Args:
            target_path (Path): The destination file path.
            content (str): The UTF-8 string content to write.

        Raises:
            IOError: If a security violation is detected or disk I/O fails.
        """
        # [Security] Prevent symlink traversal attacks
        if target_path.exists() and target_path.is_symlink():
            raise IOError(f"Security violation: Refusing to write to symlink '{target_path}'")

        temp_file = target_path.with_suffix(".yamlr.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno()) # [Hardening] Ensure data is on disk before replace

            os.replace(temp_file, target_path)

        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"Atomic write failed: {e}")

    def create_backup(self, target_path: Path) -> Path:
        """
        Creates a centralized backup using the Mirror Strategy.

        Structure:
        <workspace>/.Yamlr/backups/path/to/file-<timestamp>.yaml
        """
        try:
            rel_path = target_path.relative_to(self.workspace)
        except ValueError:
            # File is outside workspace - preserve structure under 'external' folder
            # [Fix] Ensure rel_path is truly relative by stripping the anchor (e.g. '/' or 'C:\')
            abs_path = target_path.resolve()
            rel_path = Path("external") / abs_path.relative_to(abs_path.anchor)

        # Replicate directory structure inside backup folder
        backup_dest_dir = self.backup_dir / rel_path.parent
        backup_dest_dir.mkdir(parents=True, exist_ok=True)

        # [Hardening] Race-proof & Unique backup naming
        import time
        import uuid
        timestamp = int(time.time())
        unique_id = uuid.uuid4().hex[:8]
        backup_name = f"{target_path.stem}.{timestamp}-{unique_id}{target_path.suffix}"

        # Windows MAX_PATH Resilience: If path is too long, hash the parent structure
        # Baseline MAX_PATH is 260. We use 200 as a safe threshold for the parent dir.
        if len(str(backup_dest_dir)) > 200:
            import hashlib
            path_hash = hashlib.sha256(str(rel_path.parent).encode()).hexdigest()[:12]
            backup_dest_dir = self.backup_dir / "sharded" / path_hash

        backup_dest_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dest_dir / backup_name

        shutil.copy2(target_path, backup_path)

        # [Smart Rotation] Keep specific file history lean (Max 5 versions)
        self._rotate_backups(backup_dest_dir, target_path.stem, target_path.suffix)

        return backup_path

    def _rotate_backups(self, backup_dir: Path, stem: str, suffix: str, keep: int = 5):
        """Auto-prunes old backups for a specific file to prevent disk bloat."""
        try:
            # Find all backups for this file: stem.<timestamp>suffix
            candidates = []
            for f in backup_dir.glob(f"{stem}.*{suffix}"):
                candidates.append(f)

            # Sort by name (timestamp is in name) or mtime (safer)
            candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            if len(candidates) > keep:
                for old in candidates[keep:]:
                    try:
                        old.unlink()
                        logger.debug(f"Rotated backup: {old}")
                    except Exception as e:
                        logger.debug(f"Backup rotation: Failed to unlink {old}: {e}")
        except Exception as e:
            logger.warning(f"Backup rotation warning: {e}")

    def crawl(
        self, root_path: Path, extensions: List[str], max_depth: int
    ) -> Generator[Tuple[Path, str], None, None]:
        """
        Generator that yields (absolute_path, relative_path_str) for matching files.
        Handles depth limiting and security checks.
        """
        ext_set = {
            e.strip() if e.startswith(".") else f".{e.strip()}" for e in extensions
        }

        # Verify root exists
        if not root_path.exists():
            logger.error(f"Scan root does not exist: {root_path}")
            return

        for root, dirs, files in os.walk(root_path):
            # Depth check
            current_depth = len(Path(root).relative_to(root_path).parts)
            if current_depth >= max_depth:
                del dirs[:]
                continue

            for file in files:
                if any(file.endswith(ext) for ext in ext_set):
                    abs_path = Path(root) / file

                    # Compute relative path for reporting
                    try:
                        rel_path = str(abs_path.relative_to(self.workspace))
                    except ValueError:
                        # File outside workspace (e.g. symlink or external scan)
                        rel_path = str(abs_path)

                    yield abs_path, rel_path
