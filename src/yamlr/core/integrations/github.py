#!/usr/bin/env python3
"""
Yamlr GITHUB INTEGRATION - The PR Feedback Loop
-----------------------------------------------
Handles interactions with the GitHub API for Pull Request feedback.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("yamlr.integrations.github")


class GitHubPRClient:
    """
    A lightweight, zero-dependency client for GitHub PR comments.

    Why: To avoid external dependencies (like PyGithub) in the core action
         runtime while providing robust PR feedback capabilities.
    """

    def __init__(self, token: str, repository: str, pr_number: int):
        self.token = token
        self.repository = repository
        self.pr_number = pr_number
        self.base_url = f"https://api.github.com/repos/{repository}"

    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "Yamlr-Action",
        }

        req_data = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            logger.error(f"GitHub API Error ({e.code}): {e.read().decode('utf-8')}")
            raise
        except Exception as e:
            logger.error(f"GitHub Request Failed: {e}")
            raise

    def get_comments(self) -> List[Dict[str, Any]]:
        """Retrieves all comments for the current PR."""
        return self._request("GET", f"issues/{self.pr_number}/comments")

    def create_comment(self, body: str) -> Dict[str, Any]:
        """Creates a new comment on the PR."""
        return self._request("POST", f"issues/{self.pr_number}/comments", {"body": body})

    def update_comment(self, comment_id: int, body: str) -> Dict[str, Any]:
        """Updates an existing comment."""
        return self._request("PATCH", f"issues/{comment_id}", {"body": body})

    def find_yamlr_comment(self) -> Optional[int]:
        """Finds the ID of an existing Yamlr PR comment."""
        comments = self.get_comments()
        for comment in comments:
            if "<!-- yamlr-comment-id -->" in comment.get("body", ""):
                return comment["id"]
        return None

    def post_or_update_comment(self, body: str):
        """
        Maintains a single persistent Yamlr comment on the PR.
        """
        # Wrap the body in a hidden identifier tag
        wrapped_body = f"{body}\n\n<!-- yamlr-comment-id -->"

        comment_id = self.find_yamlr_comment()
        if comment_id:
            logger.info(f"Updating existing Yamlr comment: {comment_id}")
            self.update_comment(comment_id, wrapped_body)
        else:
            logger.info("Creating new Yamlr comment.")
            self.create_comment(wrapped_body)


def get_pr_context() -> Optional[Dict[str, Any]]:
    """
    Extracts GitHub PR context from environment variables.
    """
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")

    # Try to find PR number from GITHUB_EVENT_PATH
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return None

    try:
        with open(event_path, "r") as f:
            event_data = json.load(f)

        pr_number = event_data.get("pull_request", {}).get("number")
        if not pr_number and event_data.get("issue", {}).get("number"):
            # Fallback for issue-related events
            pr_number = event_data["issue"]["number"]

        if repo and token and pr_number:
            return {"repository": repo, "token": token, "pr_number": int(pr_number)}
    except Exception as e:
        logger.error(f"Failed to parse GitHub event context: {e}")

    return None
