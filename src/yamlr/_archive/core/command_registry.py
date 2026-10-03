"""Universal Command Registry — centralized command metadata and tier definitions."""


class UniversalCommandRegistry:
    """Centralized command metadata for tier gating and help rendering."""

    COMMANDS = {
        # --- Pro Commands ---
        "dna": {"desc": "Generate immutable semantic integrity signatures.", "pro": True},
        "drift": {"desc": "Reconcile live cluster state against source of truth.", "pro": False},
        "audit": {"desc": "Fleet-wide cross-resource analysis and scoring.", "pro": False},
        "graph": {"desc": "Visualize manifest topology and blast radius.", "pro": False},
        "pulse": {"desc": "Real-time manifest integrity monitoring.", "pro": True},
        "fleet": {"desc": "Manage large-scale multi-cluster manifest audits.", "pro": True},
        "secure": {"desc": "Apply autonomous security hardening policies.", "pro": True},
        "rollback": {"desc": "Atomic reversal of the last remediation session (alias of restore).", "pro": True},
        "evidence": {"desc": "Collect and package forensic audit evidence.", "pro": True},
        "roi": {"desc": "Calculate manifest engineering quality and reliability impact metrics.", "pro": True},
        "impact": {"desc": "Calculate manifest engineering quality and reliability impact metrics (alias of roi).", "pro": True},
        "migrate": {"desc": "Automated API version migration.", "pro": True},
        "idp-export": {"desc": "Export safety and compliance metrics to Internal Developer Portals.", "pro": True},
        # --- Free Commands ---
        "scan": {"desc": "Forensic manifest analysis.", "pro": False},
        "heal": {"desc": "Autonomous remediation with comment preservation.", "pro": False},
        "diff": {"desc": "Preview proposed remediations side-by-side or unified.", "pro": False},
        "fmt": {"desc": "Canonical manifest formatting and schema-aware key ordering.", "pro": False},
        "fix": {"desc": "Instant schema-compliant deprecation and structure fix.", "pro": False},
        "status": {"desc": "Engine health and workspace status.", "pro": False},
        "doctor": {"desc": "Environment diagnostics.", "pro": False},
        "version": {"desc": "Engine version.", "pro": False},
        "welcome": {"desc": "Show welcome dashboard.", "pro": False},
        "guide": {"desc": "Interactive learning guide.", "pro": False},
        "explain": {"desc": "Technical concept lookup.", "pro": False},
        "install": {"desc": "Install Git hooks and CI integrations.", "pro": False},
        "restore": {"desc": "Atomic restoration of last remediation checkpoint.", "pro": False},
        "completion": {"desc": "Generate shell completions.", "pro": False},
        "lsp": {"desc": "Start Language Server Protocol interface.", "pro": False},
        "admin": {"desc": "Administrative tasks.", "pro": False},
        "auth": {"desc": "Authenticate and manage Yamlr Pro licensing.", "pro": False},
        "subscribe": {"desc": "Upgrade Yamlr workspace to Pro tier.", "pro": False},
        "catalog": {"desc": "Browse forensic detector catalog.", "pro": True},
        "check": {"desc": "Run a single detector check.", "pro": True},
        "diagnose": {"desc": "Deep diagnostic audit of engine internals.", "pro": True},
        "init": {"desc": "Initialize a new Yamlr workspace.", "pro": False},
        "legal": {"desc": "Display license and legal metadata.", "pro": True},
        "manual": {"desc": "Open the offline professional reference.", "pro": True},
        "mcp": {"desc": "Model Context Protocol interface for IDE and editor integrations.", "pro": False},
        "verify": {"desc": "Verify manifest integrity against DNA baseline.", "pro": True},
        "rules": {"desc": "Inspect forensic rule catalog and schema coverage (alias of catalog).", "pro": True},
        "stats": {"desc": "Display engine performance and audit metrics (alias of admin stats).", "pro": False},
        "baseline": {"desc": "Establish or verify workspace baseline fingerprints.", "pro": False},
        "demo": {"desc": "Generate an interactive sample workspace with broken manifests.", "pro": False},
        "features": {"desc": "Display active engine capabilities and tier support.", "pro": False},
    }

    @classmethod
    def get_desc(cls, cmd: str) -> str:
        """Returns description for a command, or a fallback message."""
        return cls.COMMANDS.get(cmd, {}).get("desc", f"Command '{cmd}' not registered.")

    @classmethod
    def is_pro(cls, cmd: str) -> bool:
        """Returns True if the command requires a Pro license."""
        return cls.COMMANDS.get(cmd, {}).get("pro", False)
