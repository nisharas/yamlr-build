import os
import json
import urllib.request
import urllib.error

def post_pr_comment(reports: list) -> None:
    """
    Posts a summary of the Yamlr scan to the GitHub PR if running in GHA.
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
    
    # Calculate stats
    total_files = len(reports)
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

    # Sort findings to get top 3 by severity (ERROR > WARNING)
    all_findings.sort(key=lambda x: 0 if x["severity"] == "ERROR" else 1)
    top_findings = all_findings[:3]

    # Calculate average health score
    health_score = 0
    if total_files > 0:
        health_score = sum(r.get("health_score", 0) for r in reports) / total_files

    score_icon = "🟢" if health_score >= 90 else "🟡" if health_score >= 70 else "🔴"

    body = f"### 🛡️ Yamlr Guard Security & Health Report\n\n"
    body += f"**Repository Health:** {score_icon} **{health_score:.1f}/100**\n"
    body += f"**Files Scanned:** {total_files}\n"
    body += f"**Total Issues Detected:** {total_issues}\n\n"

    if top_findings:
        body += "#### 🚨 Top Findings\n"
        for finding in top_findings:
            icon = "❌" if finding["severity"] == "ERROR" else "⚠️"
            body += f"- {icon} **{finding['rule_id']}**: {finding['message']}\n"
    
    body += "\n---\n"
    body += "💡 *Run `yamlr heal .` locally to automatically fix these issues and view the cryptographic DNA receipts.*"

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
        with urllib.request.urlopen(req) as response: # nosec B310
            pass # Successfully posted comment
    except Exception as e:
        print(f"Failed to post PR comment: {e}")
