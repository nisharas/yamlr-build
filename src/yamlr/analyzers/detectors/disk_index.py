#!/usr/bin/env python3
"""
Yamlr DISK-BACKED INDEX
-----------------------
Provides a memory-efficient SQLite-backed indexing strategy for ultra-scale
Kubernetes repositories (>100k manifests).

Why: To eliminate OOM crashes in the master process by avoiding the collection 
     of all manifest identities into a single Python list.
"""

import json
import logging
import os
import sqlite3
import tempfile
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Set

if TYPE_CHECKING:
    from yamlr.models import ManifestIdentity

logger = logging.getLogger("yamlr.analyzer.disk_index")

class DiskIndex:
    """
    SQLite-backed index for resource lookup.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.temp_dir = tempfile.TemporaryDirectory(prefix="yamlr_index_")
            self.db_path = os.path.join(self.temp_dir.name, "index.db")
        else:
            self.db_path = db_path
            self.temp_dir = None
            
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._init_db()
        
    def _init_db(self):
        self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("PRAGMA synchronous=OFF")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS resources (kind TEXT, namespace TEXT, name TEXT, payload TEXT)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_lookup ON resources (kind, namespace, name)")
        self.conn.commit()
        
    def clear(self):
        """Removes all entries from the index."""
        self.cursor.execute("DELETE FROM resources")
        self.conn.commit()
        
    def add_identity(self, identity: "ManifestIdentity"):
        """Adds a complete identity to the disk index."""
        payload = json.dumps(identity.to_dict())
        self.cursor.execute(
            "INSERT INTO resources VALUES (?, ?, ?, ?)", 
            (identity.kind, identity.namespace or "default", identity.name, payload)
        )
        
    def add_all(self, identities: List["ManifestIdentity"]):
        """Batch inserts multiple identities with full payloads."""
        data = [
            (i.kind, i.namespace or "default", i.name, json.dumps(i.to_dict())) 
            for i in identities
        ]
        self.cursor.executemany("INSERT INTO resources VALUES (?, ?, ?, ?)", data)
        self.conn.commit()

    def get_all(self) -> Generator["ManifestIdentity", None, None]:
        """Retrieves all identities as a generator of ManifestIdentity objects."""
        from yamlr.models import ManifestIdentity
        self.cursor.execute("SELECT payload FROM resources")
        while True:
            row = self.cursor.fetchone()
            if row is None:
                break
            yield ManifestIdentity.from_dict(json.loads(row[0]))
        
    def commit(self):
        """Finalizes the index."""
        self.conn.commit()
        
    def exists(self, kind: str, namespace: str, name: str) -> bool:
        """Checks if a resource exists in the index."""
        self.cursor.execute(
            "SELECT 1 FROM resources WHERE kind=? AND namespace=? AND name=? LIMIT 1",
            (kind, namespace, name)
        )
        return self.cursor.fetchone() is not None

    def get_filenames(self) -> List[str]:
        """Retrieves list of files indexed (legacy placeholder)."""
        self.cursor.execute("SELECT DISTINCT kind FROM resources") # Kind used as proxy if file_path missing
        return [r[0] for r in self.cursor.fetchall()]

    def close(self):
        """Cleanup."""
        self.conn.close()
        if self.temp_dir:
            self.temp_dir.cleanup()

    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def to_memory_index(self) -> Dict[str, Dict[str, Set[str]]]:
        """
        Converts the disk index back to a memory index (only if small enough).
        Used for backward compatibility with existing detectors.
        """
        self.cursor.execute("SELECT kind, namespace, name FROM resources")
        index = {}
        for k, ns, name in self.cursor.fetchall():
            index.setdefault(k, {}).setdefault(ns, set()).add(name)
        return index
