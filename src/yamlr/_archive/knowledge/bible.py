"""Authoritative reference documentation resolver for commands, flags, and rules."""

import os
import re
from typing import Any, Dict, List, Optional


class BiblicalRegistry:
    """The authoritative documentation engine that parses Man Pages at runtime."""

    def __init__(self, man_path: str = "docs/man/man1"):
        self.man_path = man_path
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy-initializes the registry on first lookup."""
        if self._initialized:
            return
        self._initialized = True
        if not os.path.exists(self.man_path):
            return

        for filename in os.listdir(self.man_path):
            if filename.endswith(".1"):
                cmd_name = filename.replace("yamlr-", "").replace(".1", "")
                full_path = os.path.join(self.man_path, filename)
                # We still store the path, but we will parse on-demand
                self.cache[cmd_name] = {"path": full_path, "dossier": None}

    def _get_dossier(self, command: str) -> Optional[Dict[str, Any]]:
        """Parses a specific man page on-demand."""
        self._ensure_initialized()
        cmd_info = self.cache.get(command.lower())
        if not cmd_info:
            return None
        
        if cmd_info["dossier"] is None:
            cmd_info["dossier"] = self._parse_man_page(cmd_info["path"])
        
        return cmd_info["dossier"]

    def _parse_man_page(self, path: str) -> Dict[str, Any]:
        """Parses a ROFF man page into a structured forensic dossier."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        dossier = {
            "title": "",
            "description": "",
            "synopsis": "",
            "options": {},
            "raw": content
        }

        # Extract Title
        title_match = re.search(r'\.TH\s+"([^"]+)"', content)
        if title_match:
            dossier["title"] = title_match.group(1).replace("-", " ").title()

        # Extract Description (Layer 2)
        desc_match = re.search(r'\.SH "DESCRIPTION"\n(.*?)\.PP', content, re.DOTALL)
        if desc_match:
            dossier["description"] = desc_match.group(1).strip().replace("\\-", "-")

        # Extract Options/Flags (Layer 3)
        # Pattern: \fB--flag <ARG>\fR: Description
        options = {}
        # This regex handles flags with or without arguments inside the bold tags
        opt_matches = re.finditer(r'\\fB(?:\\fB)?(--[a-z0-9-]+).*?\\fR(?:\\fR)?:\s*(.*)', content)
        for m in opt_matches:
            flag = m.group(1)
            desc = m.group(2).strip().replace("\\-", "-")
            options[flag] = desc
        
        dossier["options"] = options
        return dossier

    def lookup(self, command: str, flag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Layered lookup for commands and flags."""
        cmd_data = self._get_dossier(command)
        if not cmd_data:
            return None

        # Clean ROFF tags for display (strip ROFF tags)
        def clean_roff(text):
            for tag in ['\\fB', '\\fR', '\\fI', '\\fP', '\\f(BI', '\\f(PI']:
                text = text.replace(tag, '')
            text = text.replace('\\&', '')
            text = text.replace('\\-', '-')
            return text.strip()

        if flag:
            flag_desc = cmd_data["options"].get(flag)
            if flag_desc:
                return {
                    "title": f"Flag: {flag}",
                    "definition": clean_roff(flag_desc),
                    "rationale": f"Explicit configuration for the '{command}' logic branch.",
                    "impact": "Operational modification"
                }
            return None

        # Extract a more substantial definition if possible
        raw_desc = cmd_data["description"] or ""
        definition = clean_roff(raw_desc.split(".PP")[0]) if ".PP" in raw_desc else clean_roff(raw_desc)

        return {
            "title": cmd_data["title"],
            "definition": definition or "Technical command interface.",
            "rationale": f"Authoritative documentation for 'yamlr {command}'.",
            "impact": "Production Reliability Standard",
            "options_count": len(cmd_data["options"])
        }

# Global Instance
BIBLE = BiblicalRegistry()
