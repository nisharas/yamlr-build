import os
import json
import difflib
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple
__all__ = ['post_pr_comment']


def post_pr_comment(reports: List[Any]) -> None:
    """
    Posts a summary of the Yamlr scan to the GitHub PR if running in GHA.
    
    Why: To provide immediate, actionable feedback to developers directly 
         within the pull request workflow, highlighting repairs and health.
    """
    token = os.environ.get("INPUT_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return

    from yamlr.core.bridge import YamlrBridge
    if YamlrBridge.is_offline_mode():
        return

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event_data = json.load(f)

    # Only run on pull requests
    if "pull_request" not in event_data:
        return

    pr_number = event_data["pull_request"]["number"]
    repo_full_name = event_data["repository"]["full_name"]
    
    # Calculate stats and top findings
    total_issues, top_findings = _extract_findings(reports)
    total_files = len(reports)

    # Calculate health score meta
    dna_integrity_score, score_icon = _calculate_health_meta(reports)

    body = _build_comment_body(
        dna_integrity_score=dna_integrity_score,
        score_icon=score_icon,
        total_files=total_files,
        total_issues=total_issues,
        top_findings=top_findings,
        reports=reports
    )

    url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
    data = json.dumps({"body": body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("Content-Type", "application/json")

    # [Security] Validate scheme to prevent SSRF or unauthorized file access
    if not url.startswith("https://"):
        return

    try:
        with urllib.request.urlopen(req) as _: # nosec B310
            pass # Successfully posted comment
    except Exception as e:
        import logging
        logging.getLogger("yamlr").error(f"Failed to post PR comment: {e}")

def _extract_findings(reports: List[Any]) -> Tuple[int, List[Dict[str, str]]]:
    """Extracts total issue count and top findings from reports."""
    total_issues = 0
    all_findings = []
    
    for r in reports:
        findings = r.get("findings", [])
        total_issues += len(findings)
        for f in findings:
            all_findings.append({
                "rule_id": f.get("rule_id", "Unknown"),
                "severity": f.get("severity", "WARNING"),
                "message": f.get("message", "No message")
            })

    # Sort: ERROR (0) < WARNING (1)
    all_findings.sort(key=lambda x: 0 if x["severity"] == "ERROR" else 1)
    return total_issues, all_findings[:3]

def _calculate_health_meta(reports: List[Any]) -> Tuple[float, str]:
    """Calculates average health score and corresponding icon."""
    if not reports:
        return 0.0, "⚪"
    
    avg_score = sum(r.get("dna_integrity_score", 0) for r in reports) / len(reports)
    
    if avg_score >= 90:
        icon = "🟢"
    elif avg_score >= 70:
        icon = "🟡"
    else:
        icon = "🔴"
        
    return avg_score, icon

def _build_comment_body(
    dna_integrity_score: float, 
    score_icon: str, 
    total_files: int, 
    total_issues: int, 
    top_findings: List[Dict[str, str]], 
    reports: List[Any]
) -> str:
    """Constructs the markdown body for the PR comment."""
    body = "### 🛡️ Yamlr Guard Security & Health Report\n\n"
    body += f"**Repository Health:** {score_icon} **{dna_integrity_score:.1f}/100**\n"
    body += f"**Files Scanned:** {total_files}\n"
    body += f"**Total Issues Detected:** {total_issues}\n\n"

    if top_findings:
        body += "#### 🚨 Top Findings\n"
        for finding in top_findings:
            icon = "❌" if finding["severity"] == "ERROR" else "⚠️"
            body += f"- {icon} **{finding['rule_id']}**: {finding['message']}\n"
    
    diff_summary = _generate_diff_summary(reports)
    if diff_summary:
        body += "\n#### 🔧 Proposed Repairs (Diff Summary)\n"
        body += diff_summary

    body += "\n---\n"
    body += "💡 *Run `yamlr heal .` locally to automatically fix these issues and view the cryptographic DNA receipts.*"
    return body

def _generate_diff_summary(reports: List[Any], max_length: int = 50000) -> str:
    """
    Generates a bundled diff summary for all healed files.
    
    Why: Allows developers to preview repairs without leaving the PR.
    """
    summary_parts = []
    total_len = 0
    
    changed_reports = [r for r in reports if r.get("healed_content") and r.get("raw_content") != r.get("healed_content")]
    
    if not changed_reports:
        return ""

    for r in changed_reports:
        file_path = r.get("file_path", "Unknown")
        raw = r.get("raw_content", "")
        healed = r.get("healed_content", "")
        
        diff = list(difflib.unified_diff(
            raw.splitlines(keepends=True),
            healed.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=2
        ))
        
        if not diff:
            continue
            
        diff_text = "".join(diff)
        part = f"<details>\n<summary>📦 Fix Preview: <code>{file_path}</code></summary>\n\n"
        part += f"```diff\n{diff_text}```\n\n</details>\n"
        
        if total_len + len(part) > max_length:
            summary_parts.append("\n> [!NOTE]\n> Remaining diffs truncated to fit GitHub comment limits.")
            break
            
        summary_parts.append(part)
        total_len += len(part)

    return "\n".join(summary_parts)
