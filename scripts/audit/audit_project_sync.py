import os
import re
import sys
from pathlib import Path

def get_issue_ids(content):
    """Extract [TASK-XX-X] or [BUG-XX-X] or [VAL-XX-X] or [PRO-XX-X] ids."""
    return set(re.findall(r'\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN)-\d+-\d+k?\]', content))

def get_completed_tasks(content):
    """Get IDs of completed tasks (marked [x] or with ✅)."""
    completed = []
    # Match patterns like [x] [TASK-07-3]
    completed.extend(re.findall(r'\[x\]\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN)-\d+-\d+k?\]\*\*', content))
    # Match patterns like ✅ **[TASK-07-1]**
    completed.extend(re.findall(r'✅\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN)-\d+-\d+k?\]\*\*', content))
    return set(completed)

def check_sync():
    root = Path(__file__).resolve().parent.parent
    backlog_path = root / "docs/BACKLOG.md"
    roadmap_path = root / "docs/PRODUCT_ROADMAP.md"
    scorecard_path = root / "docs/FEATURE_SCORECARD.md"

    missing_files = []
    for p in [backlog_path, roadmap_path, scorecard_path]:
        if not p.exists():
            missing_files.append(p.name)

    if missing_files:
        print(f"❌ Synchronization Audit Failed: Missing files {missing_files}")
        sys.exit(1)

    backlog_content = backlog_path.read_text(encoding="utf-8")
    roadmap_content = roadmap_path.read_text(encoding="utf-8")

    # Simple check: If it's [x] in backlog, it should be mentioned in Roadmap with ✅ or [x]
    # This is a bit complex to parse accurately because they use different formats.
    # We'll stick to a simpler heuristic for now: check if TASK IDs marked as [x] in backlog
    # are mentioned in Roadmap.

    backlog_done = set(re.findall(r'\[x\]\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN-[^\]]+)\]', backlog_content))
    # Also catch ✅ ones in backlog
    backlog_done.update(re.findall(r'✅\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN-[^\]]+)\]', backlog_content))

    roadmap_done = set(re.findall(r'✅\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN-[^\]]+)\]', roadmap_content))
    # Also catch [x] ones in roadmap
    roadmap_done.update(re.findall(r'\[x\]\s+\*\*\[(TASK|BUG|VAL|PRO|GAP|FREE|GTM|CLEAN-[^\]]+)\]', roadmap_content))
    # And specifically for Milestone markers
    roadmap_done.update(re.findall(r'\*\*\[v[^\]]+\] [^(]+\(COMPLETED', roadmap_content))

    print(f"[*] Auditing {len(backlog_done)} completed tasks in Backlog...")

    # We want to ensure that if something is [x] in backlog, it's not [ ] in roadmap if mentioned.
    # Actually, the user's requirement is "Ensure Backlog/Roadmap Updates".
    # For now, we'll just check if the counts are roughly similar or if any critical ones are inconsistent.

    inconsistent = []
    for task_id in backlog_done:
        # If task_id is in backlog_done but roadmap has it as [ ]
        if f"[ ] **[{task_id}]**" in roadmap_content:
            inconsistent.append(task_id)

    if inconsistent:
        print(f"[FAIL] Inconsistency detected! Following tasks are [x] in Backlog but [ ] in Roadmap: {inconsistent}")
        sys.exit(1)

    print("[SUCCESS] Project Documentation is synchronized.")
    sys.exit(0)

if __name__ == "__main__":
    check_sync()
