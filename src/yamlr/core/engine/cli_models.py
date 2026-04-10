#!/usr/bin/env python3
"""
Yamlr CLI REGISTRY MODELS
-------------------------
Defines the declarative schema for CLI commands and flags.

Why: To eliminate 'Skeleton Debt' and enable dynamic help generation,
     ensuring the CLI is platform-ready for rapid extension.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class FlagDefinition(BaseModel):
    """
    Declarative definition of a CLI flag.
    """
    name: str
    shorthand: Optional[str] = None
    description: str
    type: str = "bool"
    default: Any = None
    required: bool = False
    hidden: bool = False

class CLICommand(BaseModel):
    """
    Declarative definition of a Yamlr CLI command.
    """
    name: str
    alias: Optional[str] = None
    description: str
    flags: List[FlagDefinition] = Field(default_factory=list)
    tier: str = "Free"  # 'Free' or 'Pro'
    category: str = "Core"
    
    def to_help_string(self) -> str:
        """Generates a standardized help string for the CLI."""
        return f"{self.name}: {self.description}"
