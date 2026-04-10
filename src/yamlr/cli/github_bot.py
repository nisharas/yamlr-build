import logging
import os
from typing import Any, List, Optional

from yamlr.core.advisory import GitHubAdvisoryRenderer
from yamlr.core.integrations.github import GitHubPRClient, get_pr_context

logger = logging.getLogger("yamlr.cli.github_bot")
__all__ = ["post_pr_comment"]


def post_pr_comment(results: List[Any], is_dry_run: bool = True) -> None:
    """
    Maintains a high-fidelity, idempotent PR comment with Yamlr findings.

    Why: To provide immediate, visual, and non-spammy feedback to developers
         directly within their PR workflow.
    """
    # 1. Connectivity Check
    from yamlr.core.bridge import YamlrBridge

    if YamlrBridge.is_offline_mode():
        return

    # 2. Context Extraction
    ctx = get_pr_context()
    if not ctx:
        logger.debug("GitHub PR context not found. Skipping comment.")
        return

    # 3. Report Generation
    try:
        renderer = GitHubAdvisoryRenderer()
        body = renderer.render_comment(results, is_dry_run=is_dry_run)

        # 4. API Execution (Idempotent)
        client = GitHubPRClient(token=ctx["token"], repository=ctx["repository"], pr_number=ctx["pr_number"])

        client.post_or_update_comment(body)
        logger.info(f"Successfully synced Yamlr comment to PR #{ctx['pr_number']}")

    except Exception as e:
        logger.error(f"Failed to post GitHub PR comment: {e}")
