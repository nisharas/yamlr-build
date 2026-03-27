"""
Yamlr CLI Constants & Tiering
-----------------------------
Defines the categorization of CLI commands for tiered discovery.

Why: To maintain a clean public API surface while preserving advanced power-user features.
"""

from enum import Enum, auto

class CommandTier(Enum):
    """
    Categorizes commands based on the user journey.
    """
    PRIMARY = auto()     # START HERE: scan, heal, check
    SECONDARY = auto()   # WHEN YOU'RE READY: upgrade, status, doctor, rules, explain
    ADVANCED = auto()    # Hidden by default: Everything else (Insights, Pipeline, Meta)

# Mapping of command -> Tier for journey-based discovery
COMMAND_TIER_MAP = {
    # PRIMARY: Start Here (The Front Door)
    "scan": CommandTier.PRIMARY,
    "heal": CommandTier.PRIMARY,
    "check": CommandTier.PRIMARY,
    "audit": CommandTier.PRIMARY,  # Twin for scan

    # SECONDARY: When You're Ready (Deeper Analysis & Day 2)
    "upgrade": CommandTier.SECONDARY,
    "migrate": CommandTier.SECONDARY, # Twin for upgrade
    "status": CommandTier.SECONDARY,
    "doctor": CommandTier.SECONDARY,
    "rules": CommandTier.SECONDARY,
    "explain": CommandTier.SECONDARY,
    "secure": CommandTier.SECONDARY, # Hardening is a Day-2 maturity step

    # ADVANCED: Power User / Pipelines / Meta (Hidden unless --all)
    "graph": CommandTier.ADVANCED,
    "stats": CommandTier.ADVANCED,
    "roi": CommandTier.ADVANCED,
    "pulse": CommandTier.ADVANCED,
    "idp-export": CommandTier.ADVANCED,
    "mcp": CommandTier.ADVANCED,
    "dna": CommandTier.ADVANCED,
    "evidence": CommandTier.ADVANCED,
    "baseline": CommandTier.ADVANCED,
    "welcome": CommandTier.ADVANCED,
    "manual": CommandTier.ADVANCED,
    "demo": CommandTier.ADVANCED,
    "init": CommandTier.ADVANCED,
    "restore": CommandTier.ADVANCED,
    "diagnose": CommandTier.ADVANCED,
    "completion": CommandTier.ADVANCED,
    "catalog": CommandTier.ADVANCED,
    "version": CommandTier.ADVANCED,
    "auth": CommandTier.ADVANCED,
}
